from flask import request, jsonify
from database.dbConnection import get_db_connection

def get_file_data_controller():
    """
    GET API to dynamically fetch file status columns from file_master table
    Returns: All file metadata with status columns extracted dynamically
    
    Query Parameters:
    - file_name (required): Name of the uploaded file
    - session_id (optional): Session ID, default is '123456'
    
    Example: /get_file_data?file_name=customers_orders_1&session_id=123456
    """
    try:
        # Step 1: Get request parameters
        file_name = request.args.get("file_name")
        session_id = request.args.get("session_id", "123456")
        
        # Step 2: Validation
        if not file_name:
            return jsonify({
                "status": "failed",
                "statusCode": 400,
                "message": "file_name is required",
                "data": {}
            }), 400

        # Step 3: Connect to database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Step 4: Call stored procedure to fetch file status dynamically
        cursor.callproc('sp_get_file_status', (file_name, session_id))
        
        file_status_data = None
        for result in cursor.stored_results():
            file_status_data = result.fetchone()
        
        cursor.close()
        conn.close()

        # Step 5: Check if file exists
        if not file_status_data or file_status_data.get('status') == 'FILE_NOT_FOUND':
            return jsonify({
                "status": "failed",
                "statusCode": 404,
                "message": "File not found in file_master table",
                "data": {}
            }), 404

        # Step 6: Build flat response - all keys directly in data object
        # Exclude only 'id' and 'status' fields
        exclude_fields = {'id', 'status'}
        
        response_data = {}
        for key, value in file_status_data.items():
            if key not in exclude_fields:
                # Convert datetime to string if needed
                if key in ['created_at', 'updated_at']:
                    response_data[key] = str(value) if value else ''
                else:
                    response_data[key] = value

        return jsonify({
            "status": "success",
            "statusCode": 200,
            "message": "File status metadata retrieved successfully",
            "data": response_data
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "statusCode": 500,
            "message": "Failed to retrieve file status",
            "error": str(e),
            "data": {}
        }), 500