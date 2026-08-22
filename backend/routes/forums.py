"""Forum routes (posts + replies).

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_forum_routes(api_router, ...)`.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException


def attach_forum_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    ForumPost,
    ForumPostCreate,
    ForumReply,
    ForumReplyCreate,
):
    @api_router.post("/forums/posts", response_model=ForumPost)
    async def create_forum_post(post_data: ForumPostCreate, current_user: User = Depends(get_current_user)):
        char_doc = await db.characters.find_one({"id": post_data.character_id})
        if not char_doc or char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Character not found or not authorized")

        post = ForumPost(
            user_id=current_user.id,
            username=current_user.username,
            character_id=post_data.character_id,
            character_name=char_doc['name'],
            title=post_data.title,
            content=post_data.content,
            category=post_data.category,
            nation=post_data.nation
        )

        post_doc = post.model_dump()
        post_doc['created_at'] = post_doc['created_at'].isoformat()

        await db.forum_posts.insert_one(post_doc)
        return post

    @api_router.get("/forums/posts", response_model=List[ForumPost])
    async def get_forum_posts(nation: Optional[str] = None, category: Optional[str] = None):
        query = {}
        if nation:
            query['nation'] = nation
        if category:
            query['category'] = category

        posts = await db.forum_posts.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        for post in posts:
            if isinstance(post.get('created_at'), str):
                post['created_at'] = datetime.fromisoformat(post['created_at'])
        return posts

    @api_router.get("/forums/posts/{post_id}", response_model=ForumPost)
    async def get_forum_post(post_id: str):
        post_doc = await db.forum_posts.find_one({"id": post_id}, {"_id": 0})
        if not post_doc:
            raise HTTPException(status_code=404, detail="Post not found")
        if isinstance(post_doc.get('created_at'), str):
            post_doc['created_at'] = datetime.fromisoformat(post_doc['created_at'])
        return ForumPost(**post_doc)

    @api_router.post("/forums/posts/{post_id}/replies", response_model=ForumReply)
    async def create_reply(post_id: str, reply_data: ForumReplyCreate, current_user: User = Depends(get_current_user)):
        post_doc = await db.forum_posts.find_one({"id": post_id})
        if not post_doc:
            raise HTTPException(status_code=404, detail="Post not found")

        char_doc = await db.characters.find_one({"id": reply_data.character_id})
        if not char_doc or char_doc['user_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Character not found or not authorized")

        reply = ForumReply(
            post_id=post_id,
            user_id=current_user.id,
            username=current_user.username,
            character_id=reply_data.character_id,
            character_name=char_doc['name'],
            content=reply_data.content
        )

        reply_doc = reply.model_dump()
        reply_doc['created_at'] = reply_doc['created_at'].isoformat()

        await db.forum_replies.insert_one(reply_doc)
        await db.forum_posts.update_one({"id": post_id}, {"$inc": {"replies_count": 1}})
        return reply

    @api_router.get("/forums/posts/{post_id}/replies", response_model=List[ForumReply])
    async def get_post_replies(post_id: str):
        replies = await db.forum_replies.find({"post_id": post_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
        for reply in replies:
            if isinstance(reply.get('created_at'), str):
                reply['created_at'] = datetime.fromisoformat(reply['created_at'])
        return replies
