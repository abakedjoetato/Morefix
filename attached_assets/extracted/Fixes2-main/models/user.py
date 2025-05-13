import logging
from datetime import datetime
from database import get_collection

logger = logging.getLogger(__name__)

def create_user(user_data):
    """
    Create a new user in the database
    
    Args:
        user_data (dict): User data to insert
        
    Returns:
        dict: The created user document
    """
    try:
        users = get_collection("users")
        
        # Add created_at timestamp
        if "created_at" not in user_data:
            user_data["created_at"] = datetime.utcnow()
        
        # Insert user data
        result = users.insert_one(user_data)
        
        # Return the newly created user
        return users.find_one({"_id": result.inserted_id})
    
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise

def get_user(user_id):
    """
    Get a user from the database by Discord user ID
    
    Args:
        user_id (str): Discord user ID
        
    Returns:
        dict: User document or None if not found
    """
    try:
        users = get_collection("users")
        return users.find_one({"user_id": user_id})
    
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        return None

def update_user(user_id, update_data):
    """
    Update a user in the database
    
    Args:
        user_id (str): Discord user ID
        update_data (dict): MongoDB update operation
        
    Returns:
        dict: Updated user document or None if not found
    """
    try:
        users = get_collection("users")
        
        # Add updated_at timestamp if not using operators
        if not any(key.startswith('$') for key in update_data.keys()):
            update_data["updated_at"] = datetime.utcnow()
            update_data = {"$set": update_data}
        elif "$set" in update_data and "updated_at" not in update_data["$set"]:
            update_data["$set"]["updated_at"] = datetime.utcnow()
        
        # Update user
        result = users.update_one({"user_id": user_id}, update_data)
        
        if result.matched_count > 0:
            return get_user(user_id)
        return None
    
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return None

def delete_user(user_id):
    """
    Delete a user from the database
    
    Args:
        user_id (str): Discord user ID
        
    Returns:
        bool: True if deleted, False otherwise
    """
    try:
        users = get_collection("users")
        result = users.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return False

def get_all_users():
    """
    Get all users from the database
    
    Returns:
        list: List of user documents
    """
    try:
        users = get_collection("users")
        return list(users.find())
    
    except Exception as e:
        logger.error(f"Error getting all users: {e}", exc_info=True)
        return []

def count_users():
    """
    Count total users in the database
    
    Returns:
        int: Number of users
    """
    try:
        users = get_collection("users")
        return users.count_documents({})
    
    except Exception as e:
        logger.error(f"Error counting users: {e}", exc_info=True)
        return 0
