from ninja import NinjaAPI, Query, File, UploadedFile
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from typing import List, Optional
from django.db.models import Q
from django.core.cache import cache
from django.http import FileResponse
import pymongo
from datetime import datetime

from .models import User, Course, Category, Lesson
from .schemas import (
    CourseIn, CoursePatchIn, CourseOut, 
    LessonIn, LessonPatchIn, LessonOut, 
    CourseFilter
)

# ==========================================
# KONEKSI MONGODB (AUDIT LOGGING)
# ==========================================
try:
    mongo_client = pymongo.MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    mongo_db = mongo_client["lms_audit_logs"]
    log_collection = mongo_db["activity_logs"]
except Exception:
    log_collection = None

def log_activity(action: str, target: str, target_id: int, detail: dict):
    """Helper untuk menyimpan log mutasi data ke MongoDB NoSQL."""
    if log_collection is not None:
        try:
            log_collection.insert_one({
                "action": action,
                "target": target,
                "target_id": target_id,
                "timestamp": datetime.utcnow(),
                "detail": detail
            })
        except Exception:
            pass

# ==========================================
# DEFINISI THROTTLING & VERSIONING (Materi 5 & 6)
# ==========================================
class LMSAnonThrottle(AnonRateThrottle):
    rate = "60/minute"

class LMSAuthThrottle(AuthRateThrottle):
    rate = "60/minute"

apiv1 = NinjaAPI(
    title="LMS API v1", 
    version="1.0.0",
    urls_namespace="v1", 
    throttle=[LMSAnonThrottle(), LMSAuthThrottle()]
)

# --- Helper Function ---
def get_object_or_404(queryset_or_model, **kwargs):
    if hasattr(queryset_or_model, 'objects'):
        queryset_or_model = queryset_or_model.objects.all()
    try:
        return queryset_or_model.get(**kwargs)
    except Exception: 
        raise HttpError(404, "Data tidak ditemukan")

# ==========================================
# ENDPOINT: COURSE
# ==========================================

@apiv1.get('courses/', response=List[CourseOut], tags=["Course"])
@paginate(PageNumberPagination, page_size=10)
def list_courses(request, filters: CourseFilter = Query(...), ordering: str = '-id'):
    """Daftar course dengan Filter, Sort (Validated), Pagination, dan REDIS CACHING."""
    
    # 1. FIX: Validasi whitelist sorting ditaruh paling atas sebelum pembuatan Cache Key (Materi 2.3)
    allowed_fields = ['title', '-title', 'id', '-id']
    if ordering not in allowed_fields:
        ordering = '-id'

    # 2. Cek Cache menggunakan ordering yang sudah valid
    cache_key = f"courses_v1:search={filters.search}:active={filters.is_active}:sort={ordering}"
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data

    qs = Course.objects.select_related('instructor', 'category').all()
    qs = filters.filter(qs)
    qs = qs.order_by(ordering)
    
    data_list = list(qs)
    cache.set(cache_key, data_list, timeout=900) # Simpan di Redis selama 15 menit
    return data_list

@apiv1.post('courses/', response={201: CourseOut}, tags=["Course"])
def create_course(request, data: CourseIn):
    """Membuat course baru + MongoDB Logging."""
    instructor = User.objects.filter(role='INSTRUCTOR').first()
    category = get_object_or_404(Category, id=data.category_id)
    course = Course.objects.create(
        title=data.title,
        instructor=instructor,
        category=category,
        is_active=data.is_active
    )
    cache.delete_pattern("courses_v1:*") # Invalidation cache
    log_activity("CREATE", "COURSE", course.id, {"title": course.title})
    return 201, course

@apiv1.get('courses/{id}', response=CourseOut, tags=["Course"])
def detail_course(request, id: int):
    qs = Course.objects.select_related('instructor', 'category')
    return get_object_or_404(qs, id=id)

@apiv1.put('courses/{id}', response=CourseOut, tags=["Course"])
def update_course(request, id: int, data: CourseIn):
    """Full Update (PUT) + Cache Invalidation + MongoDB Logging."""
    course = get_object_or_404(Course, id=id)
    category = get_object_or_404(Category, id=data.category_id)
    
    for attr, value in data.dict().items():
        if attr == 'category_id':
            course.category = category
        else:
            setattr(course, attr, value)
    course.save()
    
    cache.delete_pattern("courses_v1:*")
    log_activity("UPDATE_FULL", "COURSE", course.id, {"title": course.title})
    return course

@apiv1.patch('courses/{id}', response=CourseOut, tags=["Course"])
def patch_course(request, id: int, data: CoursePatchIn):
    """Partial Update (PATCH) - Menyambung kembali logika yang sempat terputus."""
    course = get_object_or_404(Course, id=id)
    stored_data = data.dict(exclude_unset=True) 

    if 'category_id' in stored_data:
        category = get_object_or_404(Category, id=stored_data['category_id'])
        course.category = category
        del stored_data['category_id']

    for attr, value in stored_data.items():
        setattr(course, attr, value)
    
    course.save()
    cache.delete_pattern("courses_v1:*")
    log_activity("UPDATE_PARTIAL", "COURSE", course.id, stored_data)
    return course

@apiv1.delete('courses/{id}', response={204: None}, tags=["Course"])
def delete_course(request, id: int):
    """Menghapus course + Cache Invalidation + MongoDB Logging."""
    course = get_object_or_404(Course, id=id)
    course_id = course.id
    course_title = course.title
    course.delete()
    
    cache.delete_pattern("courses_v1:*")
    log_activity("DELETE", "COURSE", course_id, {"title": course_title})
    return 204, None

# ==========================================
# ENDPOINT: FILE UPLOAD & DOWNLOAD (Materi 7)
# ==========================================

@apiv1.post('courses/{id}/upload-image/', tags=["Course Media"])
def upload_course_image(request, id: int, file: UploadedFile = File(...)):
    """Upload gambar thumbnail untuk course (Maks 2MB, format Image)."""
    course = get_object_or_404(Course, id=id)
    
    if file.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran file gambar maksimal 2MB.")
        
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus berupa JPEG, PNG, atau WebP.")
        
    if hasattr(course, 'image'):
        course.image = file
        course.save()
        
    cache.delete_pattern("courses_v1:*")
    log_activity("UPLOAD_IMAGE", "COURSE", course.id, {"filename": file.name})
    return {"message": "Gambar cover course berhasil diupload.", "filename": file.name}

@apiv1.post('lessons/{id}/upload-attachment/', tags=["Lesson Media"])
def upload_lesson_attachment(request, id: int, file: UploadedFile = File(...)):
    """Upload file materi attachment (PDF/Slide) untuk Lesson (Maks 10MB)."""
    lesson = get_object_or_404(Lesson, id=id)
    
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, "Ukuran file attachment dokumen maksimal 10MB.")
        
    if hasattr(lesson, 'file_attachment'):
        lesson.file_attachment = file
        lesson.save()
        
    log_activity("UPLOAD_ATTACHMENT", "LESSON", lesson.id, {"filename": file.name})
    return {"message": "File materi berhasil diupload.", "filename": file.name}

@apiv1.get('lessons/{id}/download/', tags=["Lesson Media"])
def download_lesson_attachment(request, id: int):
    """Download file attachment dari Lesson menggunakan FileResponse."""
    lesson = get_object_or_404(Lesson, id=id)
    
    if not getattr(lesson, 'file_attachment', None):
        raise HttpError(404, "Lesson ini tidak memiliki file attachment materi.")
        
    file_field = lesson.file_attachment
    return FileResponse(
        file_field.open(),
        as_attachment=True,
        filename=file_field.name.split('/')[-1]
    )

# ==========================================
# ENDPOINT: COURSE CONTENT (LESSON)
# ==========================================

@apiv1.get('lessons/', response=List[LessonOut], tags=["Course Content"])
def list_lessons(request, course_id: Optional[int] = None):
    qs = Lesson.objects.select_related('course').all()
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs

@apiv1.post('lessons/', response={201: LessonOut}, tags=["Course Content"])
def create_lesson(request, data: LessonIn):
    course = get_object_or_404(Course, id=data.course_id)
    lesson = Lesson.objects.create(**data.dict())
    log_activity("CREATE", "LESSON", lesson.id, {"title": lesson.title})
    return 201, lesson

@apiv1.get('lessons/{id}', response=LessonOut, tags=["Course Content"])
def detail_lesson(request, id: int):
    return get_object_or_404(Lesson, id=id)

@apiv1.put('lessons/{id}', response=LessonOut, tags=["Course Content"])
def update_lesson(request, id: int, data: LessonIn):
    lesson = get_object_or_404(Lesson, id=id)
    for attr, value in data.dict().items():
        setattr(lesson, attr, value)
    lesson.save()
    log_activity("UPDATE_FULL", "LESSON", lesson.id, {"title": lesson.title})
    return lesson

@apiv1.patch('lessons/{id}', response=LessonOut, tags=["Course Content"])
def patch_lesson(request, id: int, data: LessonPatchIn):
    """Partial Update (PATCH) Lesson."""
    lesson = get_object_or_404(Lesson, id=id)
    stored_data = data.dict(exclude_unset=True)
    
    for attr, value in stored_data.items():
        setattr(lesson, attr, value)
        
    lesson.save()
    log_activity("UPDATE_PARTIAL", "LESSON", lesson.id, stored_data)
    return lesson

@apiv1.delete('lessons/{id}', response={204: None}, tags=["Course Content"])
def delete_lesson(request, id: int):
    lesson = get_object_or_404(Lesson, id=id)
    lesson_id = lesson.id
    lesson_title = lesson.title
    lesson.delete()
    log_activity("DELETE", "LESSON", lesson_id, {"title": lesson_title})
    return 204, None