from django.db import models
from django.contrib.auth.models import AbstractUser

# --- USER MODEL ---
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        STUDENT = 'STUDENT', 'Student'
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

# --- MANAGERS (Untuk Optimasi Query) ---
class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        # Mencegah N+1 dengan select_related (SQL JOIN)
        return self.select_related('instructor', 'category')

# --- MODELS UTAMA ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    class Meta:
        verbose_name_plural = "Categories"
    def __str__(self): return self.name

class Course(models.Model):
    title = models.CharField(max_length=255)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'INSTRUCTOR'})
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    
    objects = CourseQuerySet.as_manager() # Pasang Manager

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    class Meta:
        ordering = ['order']

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('student', 'course') # Constraint Unique#

class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'lesson')