import os
from typing import Optional, List

from pymongo import MongoClient
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from pydantic_mongo.fields import ObjectIdField
from pydantic_choices import choice


app = FastAPI()
client = MongoClient(os.environ["MONGODB_URL"])
db = client.college


genderChoice = choice(["M", "F"])


class UpdateStudentModel(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    gender: Optional[genderChoice]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "phone": "+420 777 123 456",
                "gender": "F",
            }
        }


class StudentModel(UpdateStudentModel):
    id: ObjectIdField = Field(default_factory=ObjectId, alias="_id")
    name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    gender: genderChoice = Field(...)

    class Config(UpdateStudentModel.Config):
        allow_population_by_field_name = True


@app.post("/", response_description="Add new student", response_model=StudentModel)
async def create_student(student: StudentModel = Body(...)):
    student = jsonable_encoder(student)
    new_student = db["students"].insert_one(student)
    created_student = db["students"].find_one({"_id": new_student.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_student)


@app.get("/", response_description="List all students", response_model=List[StudentModel])
async def list_students():
    students = list(db["students"].find())
    return students


@app.get("/{id}", response_description="Get a single student", response_model=StudentModel)
async def show_student(id: str):
    if (student := db["students"].find_one({"_id": id})) is not None:
        return student
    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.put("/{id}", response_description="Update a student", response_model=StudentModel)
async def update_student(id: str, student: UpdateStudentModel = Body(...)):
    student = {k: v for k, v in student.dict().items() if v is not None}

    if len(student) >= 1:
        update_result = db["students"].update_one({"_id": id}, {"$set": student})

        if update_result.modified_count == 1:
            if (updated_student := db["students"].find_one({"_id": id})) is not None:
                return updated_student

    if (existing_student := db["students"].find_one({"_id": id})) is not None:
        return existing_student

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.delete("/{id}", response_description="Delete a student")
async def delete_student(id: str):
    delete_result = db["students"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Student {id} not found")
