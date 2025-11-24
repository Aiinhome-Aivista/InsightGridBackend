from flask import request, jsonify
from database.dbConnection import get_db_connection

def get_file_data_controller():
    """
    GET API to fetch all file metadata from file_master table
    Returns: List of all files with their status metadata
    
    No parameters required - returns all files in the system
    
    Example: GET /get_file_data
    """
    try:
        # Step 1: Connect to database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Step 2: Fetch all files from file_master table
        query = """
            SELECT * FROM file_master
            ORDER BY updated_at DESC
        """
        cursor.execute(query)
        all_files = cursor.fetchall()
        
        cursor.close()
        conn.close()

        # Step 3: Check if any files exist
        if not all_files or len(all_files) == 0:
            return jsonify({
                "status": "success",
                "statusCode": 200,
                "message": "No files found in the system",
                "data": []
            }), 200

        # Step 4: Process each file and build response
        response_data = []
        exclude_fields = {'id', 'status'}
        
        for file_data in all_files:
            file_info = {}
            for key, value in file_data.items():
                if key not in exclude_fields:
                    # Convert datetime to string if needed
                    if key in ['created_at', 'updated_at']:
                        file_info[key] = str(value) if value else ''
                    else:
                        file_info[key] = value
            
            response_data.append(file_info)

        return jsonify({
            "status": "success",
            "statusCode": 200,
            "message": f"Retrieved {len(response_data)} file(s) successfully",
            "data": response_data
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "statusCode": 500,
            "message": "Failed to retrieve file data",
            "error": str(e),
            "data": []
        }), 500