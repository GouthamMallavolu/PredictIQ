"""
Check Azure Blob Storage structure to understand data organization
"""
import os
from azure.storage.blob import BlobServiceClient

def check_blob_structure():
    """List all blobs in the container to understand the structure"""
    connect_str = (os.getenv('STORAGE_CONNECTION') or 
                   os.getenv('AZURE_STORAGE_CONNECTION_STRING') or '').strip()
    container_name = (os.getenv('STORAGE_CONTAINER') or 
                     os.getenv('AZURE_STORAGE_CONTAINER') or 'snapshots').strip()
    
    if not connect_str:
        print("❌ Azure Storage connection string not found")
        print("Set AZURE_STORAGE_CONNECTION_STRING environment variable")
        return
    
    print(f"🔍 Checking blob structure in container: {container_name}")
    print("="*60)
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        
        # List all blobs
        blobs = container_client.list_blobs()
        
        csv_files = []
        folders = set()
        
        for blob in blobs:
            name = blob.name
            if name.endswith('.csv'):
                csv_files.append(name)
                print(f"📄 CSV: {name}")
            elif '/' in name:
                folder = name.split('/')[0]
                folders.add(folder)
        
        print("\n" + "="*60)
        print(f"📊 Summary:")
        print(f"   CSV files found: {len(csv_files)}")
        print(f"   Folders found: {len(folders)}")
        
        if csv_files:
            print(f"\n✅ Found CSV files:")
            for csv in csv_files[:10]:  # Show first 10
                print(f"   - {csv}")
            if len(csv_files) > 10:
                print(f"   ... and {len(csv_files) - 10} more")
        
        # Check for Merged_dataset.csv specifically
        merged_csv = [f for f in csv_files if 'Merged_dataset' in f or 'merged' in f.lower()]
        if merged_csv:
            print(f"\n✅ Found merged dataset files:")
            for f in merged_csv:
                print(f"   - {f}")
        else:
            print(f"\n⚠️  No 'Merged_dataset.csv' found")
            print(f"   Will need to merge individual CSV files")
        
        if folders:
            print(f"\n📁 Folders found:")
            for folder in sorted(list(folders))[:10]:
                print(f"   - {folder}/")
            if len(folders) > 10:
                print(f"   ... and {len(folders) - 10} more")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_blob_structure()

