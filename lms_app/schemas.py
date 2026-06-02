from pydantic import BaseModel
from ninja import FilterSchema, Field
from typing import List, Optional

# ==========================================
# SCHEMA: USER (NESTED)
# ==========================================
class UserOut(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True
        
# ==========================================
# SCHEMA: CATEGORY
# ==========================================
class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# ==========================================
# SCHEMA: COURSE
# ==========================================
class CourseIn(BaseModel):
    title: str = Field(..., min_length=1, example="Pemrograman Web")
    category_id: int = Field(..., example=1)
    is_active: bool = True

class CoursePatchIn(BaseModel):
    title: Optional[str] = Field(None, min_length=1, example="Pemrograman Web")
    category_id: Optional[int] = Field(None, example=1)
    is_active: Optional[bool] = None

class CourseOut(BaseModel):
    id: int
    title: str
    instructor: UserOut
    category: CategoryOut
    is_active: bool

    class Config:
        from_attributes = True

# ==========================================
# SCHEMA: COURSE CONTENT (LESSON)
# ==========================================
class LessonIn(BaseModel):
    title: str = Field(..., example="Pengenalan REST API")
    order: int = Field(default=1, example=1)
    course_id: int

class LessonPatchIn(BaseModel):
    title: Optional[str] = Field(None, example="Pengenalan REST API")
    order: Optional[int] = Field(None, example=1)
    course_id: Optional[int] = None

class LessonOut(BaseModel):
    id: int
    title: str
    order: int
    course_id: int

    class Config:
        from_attributes = True
        
# ==========================================
# SCHEMA TAMBAHAN: FILTERING & SEARCHING
# ==========================================
class CourseFilter(FilterSchema):
    search: Optional[str] = Field(None, q=['title__icontains'])
    is_active: Optional[bool] = None