import os
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

def main():
    """Connects to Azure Blob Storage and lists files in the container."""
    load_dotenv()
    connect_str = os.getenv('STORAGE_CONNECTION')
    container_name = os.getenv('STORAGE_CONTAINER', 'data')

    if not connect_str:
        print("STORAGE_CONNECTION is not set.")
        print("Please set the connection string in your .env file.")
        return

    print(f"Connecting to Azure Blob Storage container: {container_name}...")

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)

        blob_list = container_client.list_blobs()
        
        files_info = []
        for blob in blob_list:
            files_info.append({
                "Filename": blob.name,
                "Size (Bytes)": blob.size,
                "Last Modified": blob.last_modified.strftime('%Y-%m-%d %H:%M:%S')
            })

        if not files_info:
            print(f"No blobs found in container '{container_name}'.")
            return

        df = pd.DataFrame(files_info)
        print("\nFiles in container:")
        print(df.to_string())

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
