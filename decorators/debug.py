from functools import wraps
from flask import request
import time
import traceback
import logging

def debug():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the general logger from your logging setup
            logger = logging.getLogger('app.general')

            start_time = time.time()

            # Basic request info
            debug_info = []
            debug_info.append(f"\n{'='*50}")
            debug_info.append(f"🔍 DEBUG: {func.__name__}")
            debug_info.append(f"{'='*50}")
            debug_info.append(f"📥 Request: {request.method} {request.path}")
            debug_info.append(f"🌐 Full URL: {request.url}")

            # Client information
            debug_info.append(f"📍 Remote IP: {request.remote_addr}")
            debug_info.append(f"🖥️  User Agent: {request.headers.get('User-Agent', 'N/A')}")
            debug_info.append(f"🔗 Referrer: {request.headers.get('Referer', 'N/A')}")

            # Request data
            debug_info.append(f"📋 Query Parameters: {request.args.to_dict()}")
            debug_info.append(f"📝 Form Data: {request.form.to_dict()}")

            # JSON data (with error handling)
            try:
                json_data = request.get_json()
                debug_info.append(f"📄 JSON Data: {json_data}")
            except Exception as e:
                debug_info.append(f"📄 JSON Data: Error parsing JSON - {str(e)}")

            # Headers (filtered for security)
            sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'x-auth-token'}
            filtered_headers = {k: v for k, v in request.headers.items()
                              if k.lower() not in sensitive_headers}
            debug_info.append(f"📨 Headers: {dict(filtered_headers)}")

            # Files uploaded
            if request.files:
                file_info = {name: f.filename for name, f in request.files.items()}
                debug_info.append(f"📎 Files: {file_info}")

            # Route arguments (if any)
            if args or kwargs:
                debug_info.append(f"🎯 Route Args: {args}")
                debug_info.append(f"🎯 Route Kwargs: {kwargs}")

            # Session info (if available)
            try:
                from flask import session
                if session:
                    # Don't print sensitive session data, just keys
                    session_keys = list(session.keys()) if session else []
                    debug_info.append(f"🔑 Session Keys: {session_keys}")
            except:
                pass

            debug_info.append(f"⏰ Request Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Log all debug info at once
            logger.info('\n'.join(debug_info))

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Log execution time
                execution_time = time.time() - start_time
                logger.info(f"✅ Success - Execution time: {execution_time:.4f}s")
                logger.info(f"{'='*50}\n")

                return result

            except Exception as e:
                # Log errors
                execution_time = time.time() - start_time
                error_logger = logging.getLogger('app.error')
                error_logger.error(f"❌ Error occurred in {func.__name__}: {str(e)}")
                error_logger.error(f"📍 Traceback:\n{traceback.format_exc()}")
                error_logger.error(f"⏱️  Failed after: {execution_time:.4f}s")
                error_logger.error(f"{'='*50}\n")
                raise  # Re-raise the exception

        return wrapper
    return decorator
