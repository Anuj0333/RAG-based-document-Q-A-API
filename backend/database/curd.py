import uuid
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import ChatSession, Message, Document, Chunk

# def create_session():

#     db = SessionLocal()

#     session = ChatSession(
#         session_id=str(uuid.uuid4()),
#         title="New Chat"
#     )
#     db.add(session)
#     db.commit()
#     db.refresh(session)
#     db.close()

#     return session


# def get_session():
#     db = SessionLocal()
#     chats = db.query(ChatSession).all()
#     db.close()
#     return chats


# def add_message(
#     session_id,
#     role,
#     content,
# ):

#     db = SessionLocal()

#     msg = Message(

#         session_id=session_id,

#         role=role,

#         content=content,

#     )

#     db.add(msg)

#     db.commit()

#     db.close()


# def get_messages(session_id):

#     db = SessionLocal()

#     msgs = (

#         db.query(Message)

#         .filter(Message.session_id == session_id)

#         .order_by(Message.id)

#         .all()

#     )

#     db.close()

#     return msgs


def create_chat(db: Session, user_id: int):

    # db = SessionLocal()

    session = ChatSession(
        session_id=str(uuid.uuid4()),
        title = "New Chat",
        user_id=user_id
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    # db.close()
    return session

def get_all_chats(db: Session, user_id: int):

    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


def get_chat(db: Session, session_id: str, user_id: int):
    return (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        .first()
    )


def save_message(
    db: Session,
    session_id: str,
    role: str,
    content: str
):
    message = Message(
        session_id=session_id,
        role=role,
        content=content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def load_messages(db: Session, session_id: str, user_id: int):

    chat = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        .first()
    )

    if chat is None:
        return []

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id)
        .all()
    )


def delete_chat(db: Session, session_id: str, user_id: int):

    chat = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        .first()
    )

    if chat is None:
        return False

    db.query(Message).filter(
        Message.session_id == session_id
    ).delete(synchronize_session=False)

    db.delete(chat)

    db.commit()

    return True

def update_chat_title(
    db: Session,
    session_id: str,
    user_id: int,
    title: str,
):
    # print("Updating title:", session_id, user_id, title)
    # print("Title received:", title)
    chat = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        .first()
    )

    if chat:
        chat.title = title
        db.commit()
        db.refresh(chat)

    return chat


def save_document(
    db: Session,
    user_id: int,
    filename: str,
    filepath: str,
):
    existing = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.filename == filename,
        )
        .first()
    )

    if existing:
        return existing

    
    document = Document(
        user_id=user_id,
        filename=filename,
        filepath=filepath,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

def get_documents(
    db: Session,
    user_id: int,
):
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

def get_document(
    db: Session,
    user_id: int,
    filename: str,
):
    return (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.filename == filename,
        )
        .first()
    )


def delete_document(
    db: Session,
    user_id: int,
    filename: str,
):
    document = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.filename == filename,
        )
        .first()
    )

    if document is None:
        return None

    db.delete(document)
    db.commit()

    return document

def save_chunk(
    db: Session,
    user_id: int,
    filename: str,
    chunk_text: str,
    page: int,
):
    chunk = Chunk(
        user_id=user_id,
        filename=filename,
        chunk_text=chunk_text,
        page=page,
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk

def get_chunks(
    db: Session,
    user_id: int,
):
    return (
        db.query(Chunk)
        .filter(Chunk.user_id == user_id)
        .all()
    )

def delete_chunks(
    db: Session,
    user_id: int,
    filename: str,
):
    (
        db.query(Chunk)
        .filter(
            Chunk.user_id == user_id,
            Chunk.filename == filename,
        )
        .delete()
    )

    db.commit()