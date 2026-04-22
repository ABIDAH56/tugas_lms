from pydantic import BaseModel, Field
from typing import List, Optional

# --- Schema User (Nested) ---
class UserOut(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str

    # Pastikan class Config menjorok ke dalam (di dalam class UserOut)
    class Config:
        from_attributes = True
        
# --- Schema Category ---
class CategoryOut(BaseModel):
    id: int
    name: str

    # Tambahkan class Config di sini juga
    class Config:
        from_attributes = True

# --- Schema Course ---
class CourseIn(BaseModel):
    # Tambahkan min_length=1 agar tidak boleh kosong
    title: str = Field(..., min_length=1, example="Pemrograman Web")
    category_id: int = Field(..., example=1)
    is_active: bool = True

class CourseOut(BaseModel):
    id: int
    title: str
    instructor: UserOut  # Nested Schema
    category: CategoryOut
    is_active: bool

    class Config:
        from_attributes = True

# --- Schema CourseContent (Lesson) ---
class LessonIn(BaseModel):
    title: str = Field(..., example="Pengenalan REST API")
    order: int = Field(default=1, example=1)
    course_id: int

class LessonOut(BaseModel):
    id: int
    title: str
    order: int
    course_id: int

    class Config:
        from_attributes = True