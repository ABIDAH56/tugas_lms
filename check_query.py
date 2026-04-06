import os
import django
from django.db import connection, reset_queries

# Setup lingkungan Django agar script bisa jalan di luar server
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_project.settings')
django.setup()

from lms_app.models import Course

def run_demo():
    # 1. TANPA OPTIMASI (Masalah N+1)
    reset_queries()
    print("\n--- [EKSEKUSI TANPA OPTIMASI] ---")
    courses = Course.objects.all()
    for c in courses:
        # Ini memicu query baru ke database per kursus untuk ambil nama instructor
        print(f"Course: {c.title} | Instructor: {c.instructor.username}")
    print(f"Total SQL Queries: {len(connection.queries)}")

    # 2. DENGAN OPTIMASI (select_related)
    reset_queries()
    print("\n--- [EKSEKUSI DENGAN OPTIMASI (JOIN SQL)] ---")
    # Menggunakan manager .for_listing() yang sudah kita buat di models.py
    courses_opt = Course.objects.for_listing() 
    for c in courses_opt:
        # Data instructor sudah diambil di awal lewat JOIN, tidak ada query tambahan
        print(f"Course: {c.title} | Instructor: {c.instructor.username}")
    print(f"Total SQL Queries: {len(connection.queries)}")

if __name__ == "__main__":
    run_demo()