from ninja import NinjaAPI
from ninja.errors import HttpError
from typing import List, Optional
from django.db.models import Q
from .models import User, Course, Category, Lesson
from .schemas import CourseIn, CourseOut, LessonIn, LessonOut

apiv1 = NinjaAPI(title="LMS API v1", version="1.0.0")

# --- REVISI: Helper Function (Sesuai Ketentuan) ---
def get_object_or_404(queryset_or_model, **kwargs):
    """Helper yang bisa menerima Model atau QuerySet untuk mengambil objek atau raise 404."""
    
    if hasattr(queryset_or_model, 'objects'):
        queryset_or_model = queryset_or_model.objects.all()
        
    try:
        return queryset_or_model.get(**kwargs)
    except Exception: 
        raise HttpError(404, "Data tidak ditemukan")

@apiv1.get('courses/', response=List[CourseOut], tags=["Course"])
def list_courses(request, search: Optional[str] = None):
    """Mengambil semua daftar course dengan optimasi select_related."""
    qs = Course.objects.select_related('instructor', 'category').all()
    if search:
        qs = qs.filter(Q(title__icontains=search))
    return qs

@apiv1.post('courses/', response={201: CourseOut}, tags=["Course"])
def create_course(request, data: CourseIn):
    """Membuat course baru."""
    instructor = User.objects.filter(role='INSTRUCTOR').first()
    category = get_object_or_404(Category, id=data.category_id)
    course = Course.objects.create(
        title=data.title,
        instructor=instructor,
        category=category,
        is_active=data.is_active
    )
    return 201, course

@apiv1.get('courses/{id}', response=CourseOut, tags=["Course"])
def detail_course(request, id: int):
    """Detail course berdasarkan ID."""
    # Dipisah variabel qs-nya agar lebih rapi dibaca helper
    qs = Course.objects.select_related('instructor', 'category')
    return get_object_or_404(qs, id=id)

@apiv1.put('courses/{id}', response=CourseOut, tags=["Course"])
def update_course(request, id: int, data: CourseIn):
    """Update data course lengkap."""
    course = get_object_or_404(Course, id=id)
    category = get_object_or_404(Category, id=data.category_id)
    
    for attr, value in data.dict().items():
        if attr == 'category_id':
            course.category = category
        else:
            setattr(course, attr, value)
    course.save()
    return course

@apiv1.delete('courses/{id}', response={204: None}, tags=["Course"])
def delete_course(request, id: int):
    """Menghapus data course."""
    course = get_object_or_404(Course, id=id)
    course.delete()
    return 204, None

@apiv1.get('lessons/', response=List[LessonOut], tags=["Course Content"])
def list_lessons(request, course_id: Optional[int] = None):
    """Daftar konten dengan filter course_id."""
    # REVISI: Tambahkan select_related untuk menghindari N+1 problem
    qs = Lesson.objects.select_related('course').all()
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs

@apiv1.post('lessons/', response={201: LessonOut}, tags=["Course Content"])
def create_lesson(request, data: LessonIn):
    """Menambahkan konten/lesson baru ke course."""
    course = get_object_or_404(Course, id=data.course_id)
    lesson = Lesson.objects.create(**data.dict())
    return 201, lesson

@apiv1.get('lessons/{id}', response=LessonOut, tags=["Course Content"])
def detail_lesson(request, id: int):
    """Detail konten berdasarkan ID."""
    return get_object_or_404(Lesson, id=id)

@apiv1.put('lessons/{id}', response=LessonOut, tags=["Course Content"])
def update_lesson(request, id: int, data: LessonIn):
    """Mengubah data konten."""
    lesson = get_object_or_404(Lesson, id=id)
    for attr, value in data.dict().items():
        setattr(lesson, attr, value)
    lesson.save()
    return lesson

@apiv1.delete('lessons/{id}', response={204: None}, tags=["Course Content"])
def delete_lesson(request, id: int):
    """Menghapus konten."""
    lesson = get_object_or_404(Lesson, id=id)