"""Local RAG API using FastAPI."""
import os   
from rag_agent import retrieve_answer, bm25_cache
from index import ingest_pdf
from file_deletion import delete_from_qdrant
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
import shutil
import smtplib
from email.mime.text import MIMEText
from database.database import engine, SessionLocal
from database.models import User as UserModel, Document
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database.curd import (
    create_chat,
    get_all_chats,
    load_messages,
    delete_chat,
    save_message,
    save_document,
    delete_document,
    get_document,
    get_documents,
    delete_chunks
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

app = FastAPI(title="local RAG API")

# fake_db = {
#     "anuj": {
#         "username": "anuj",
#         "full_name": "Anuj Kumar Gupta",
#         "email": "anujgupta0333@gmail.com",
#         "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$v1eq1TpHiPEeI8QYw7g3hg$ohur4H+c7vE+MX90dPmgncSOaU9imGa4G6cju3gXGrw",
#         "disabled": False,
#         "is_varified": False
#     }
# }
UserModel.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str
    is_verified: bool = False

pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# function to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# function to hash password
def get_password_hash(password):
    return pwd_context.hash(password)

# getting user data from fake db
def get_user(db, username: str):
    return (
        db.query(UserModel)
        .filter(UserModel.username == username)
        .first()
    )
    # if username in db:
    #     user_data = db[username]
    #     return UserInDB(**user_data)

# authentication function  
def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    # if not user.is_verified:
    #     raise HTTPException(status_code=400, detail="Email not verified")

    return user

# Access token generation function
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes = 15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# function to get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db),):
    credentials_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# function to send verification email
def send_verification_email(to_email: str, token: str):
    verify_link = f"http://localhost:8000/verify-email?token={token}"

    subject = "Verify your email"
    body = f"Click the link to verify your email: {verify_link}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email


    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

def create_email_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=60)
    data = {"sub": email, "type" : "email_verification", "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/register")
# async def register(username: str, email :str, password: str, db: Session = Depends(get_db)):
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(UserModel)
        .filter(
            or_(
                UserModel.username == username,
                UserModel.email == email,
            )
        )
        .first()
    )
    if existing_user:
        if existing_user.username == username:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # existing_user = (
    #     db.query(UserModel)
    #     .filter(UserModel.username == username)
    #     .first()
    # )

    # if existing_user:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Username already exists"
    #     )

    hashed_password = get_password_hash(password)

    new_user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_password,
        disabled=False,
        is_verified=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

    # if username in fake_db:
    #     raise HTTPException(status_code=400, detail="User already exists")
    
    # hashed_password = get_password_hash(password)

    # fake_db["username"] = {
    #     "username": username,
    #     "email": email,
    #     "full_name": username,
    #     "hashed_password": hashed_password,
    #     "disabled": False,
    #     "is_verified": False
    # }

    # token = create_email_token(email)
    # send_verification_email(email,token)

    # return {"msg": "User registered. Please check your email to verify."}

@app.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "email_verification":
            raise HTTPException(status_code=400, detail="Invalid token type")

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(UserModel).filter(
        UserModel.email == email
    ).first()

    if user:
        user.is_verified = True
        db.commit()

        return {
            "message": "Email verified successfully"
        }

    # for user in fake_db.values():
    #     if user["email"] == email:
    #         user["is_verified"] = True
    #         return {"msg": "Email verified successfully"}
    
    raise HTTPException(status_code=404, detail="User not found")
    

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db),):
    # user = authenticate_user(fake_db, form_data.username, form_data.password)
    user = (db.query(UserModel)
        .filter(UserModel.username == form_data.username)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )
    
    # if not user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
    #                         detail="Incorrect username or password",
    #                         headers={"WWW-Authenticate": "Bearer"})
    
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/user/me",response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/user/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": 1,"owner": current_user}]


# pwd = get_password_hash("anuj123")
# print({"Password": pwd})

upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)

class ChatRequest(BaseModel):
    query: str
    session_id: str

@app.get("/")
def root():
    return {"message": "Welcome to the local RAG API!"}

@app.post("/chat")
#convert to async function
async def chat(request: ChatRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        logger.info("Query received: %s", request.query)
        # save_message(db, request.session_id, "user", request.query)
        answer = retrieve_answer(db, request.query, request.session_id, current_user.id)
        # print(answer)
        # save_message(db, request.session_id, "assistant", answer)
        return {"answer": answer}
    except Exception as e:
        logger.info("Error processing query: %s", str(e))
        return {"error": "An error occurred while processing your query."}
# def chat(request: ChatRequest):
#     try:
#         logger.info("Query received: %s", request.query)
#         answer = retrieve_answer(request.query)
#         return {"answer": answer}
#     except Exception as e:
#         logger.info("Error processing query: %s", str(e))
#         return {"error": "An error occurred while processing your query."}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user), db: Session=Depends(get_db)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        user_folder = os.path.join(upload_dir,str(current_user.id))

        os.makedirs(user_folder, exist_ok=True)

        file_location = os.path.join(user_folder, file.filename)

        if os.path.exists(file_location):
            raise HTTPException(status_code=400, detail="File already exists")

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("File uploaded successfully: %s", file.filename)

        save_document(
            db,
            current_user.id,
            file.filename,
            file_location,
        )
        
        ingest_pdf(db ,file_location, current_user.id)

        bm25_cache.pop(current_user.id, None)

        logger.info("File ingested successfully: %s", file.filename)

        return {
            "message": f"File '{file.filename}' Indexed successfully.",
            "filename": file.filename,
            "content_type": file.content_type,
            "path": file_location
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading file: %s", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while uploading the file.")


@app.get("/files")
def list_files(current_user: User = Depends(get_current_active_user), db:Session=Depends(get_db)):
    documents = get_documents(db, current_user.id)

    return {
        "files": [doc.filename for doc in documents]
    }
    # files = os.listdir(upload_dir)
    # return {"files": files}

@app.delete("/files/{filename}")
def delete_file(filename: str, current_user: User = Depends(get_current_active_user), db: Session=Depends(get_db)):

    doc = get_document(
        db,
        current_user.id,
        filename
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    file_path = doc.filepath
    # file_path = os.path.join(upload_dir, filename)
    if os.path.exists(file_path):
        delete_from_qdrant(filename, current_user.id)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

        delete_chunks(
            db,
            current_user.id,
            filename,
        )

        delete_document(
                db,
                current_user.id,
                filename,
            )
        bm25_cache.pop(current_user.id, None)
        logger.info("File deleted successfully: %s", filename)
        return {"message": f"File '{filename}' deleted successfully."}
       
    else:
        logger.warning("File not found for deletion: %s", filename)
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/sessions")
def create_session(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):

    session = create_chat(
        db,
        current_user.id
    )

    return {
        "session_id": session.session_id,
        "title": session.title
    }

@app.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # chats = get_all_chats()
    return get_all_chats(db, current_user.id)
    # return [
    #     {
    #         "session_id": c.session_id,
    #         "title": c.title
    #     }
    #     for c in chats
    # ]

@app.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    messages = load_messages(db, session_id, current_user.id)

    return {
        "messages": [
            {
                "role": m.role,
                "content": m.content,
            }
            for m in messages
        ]
    }

@app.delete("/sessions/{session_id}")
def remove_session(session_id, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):

    delete_chat(db, session_id, current_user.id)
    return {"message": "deleted"}
    # delete_chat(session_id)

    # return {
    #     "message":"deleted"
    # }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


