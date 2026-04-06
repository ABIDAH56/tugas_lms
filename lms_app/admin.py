from django.contrib import admin
from .models import User, Category, Course, Lesson, Enrollment

# Inline agar materi (Lesson) bisa diinput langsung di dalam halaman Course
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('title',)
    inlines = [LessonInline]

# Daftarkan model lainnya
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Enrollment)