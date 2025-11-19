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
        
        # List all blobs recursively
        blobs = list(container_client.list_blobs())
        
        csv_files = []
        parquet_files = []
        folders = set()
        other_files = []
        
        print(f"\n📊 Total blobs found: {len(blobs)}")
        print("="*60)
        
        for blob in blobs:
            name = blob.name
            if name.endswith('.csv'):
                csv_files.append(name)
                if len(csv_files) <= 10:  # Show first 10
                    print(f"📄 CSV: {name}")
            elif name.endswith('.parquet'):
                parquet_files.append(name)
                if len(parquet_files) <= 10:  # Show first 10
                    print(f"📦 Parquet: {name}")
            elif '/' in name:
                # Extract folder path
                parts = name.split('/')
                if len(parts) > 1:
                    folder_path = '/'.join(parts[:-1])
                    folders.add(folder_path)
            else:
                other_files.append(name)
        
        print("\n" + "="*60)
        print(f"📊 Summary:")
        print(f"   CSV files found: {len(csv_files)}")
        print(f"   Parquet files found: {len(parquet_files)}")
        print(f"   Folders found: {len(folders)}")
        print(f"   Other files: {len(other_files)}")
        
        if csv_files:
            print(f"\n✅ Found CSV files:")
            for csv in csv_files[:10]:  # Show first 10
                print(f"   - {csv}")
            if len(csv_files) > 10:
                print(f"   ... and {len(csv_files) - 10} more")
        
        if parquet_files:
            print(f"\n✅ Found Parquet files:")
            for parquet in parquet_files[:10]:  # Show first 10
                print(f"   - {parquet}")
            if len(parquet_files) > 10:
                print(f"   ... and {len(parquet_files) - 10} more")
        
        # Check for Merged_dataset.csv specifically
        merged_csv = [f for f in csv_files if 'Merged_dataset' in f or 'merged' in f.lower()]
        if merged_csv:
            print(f"\n✅ Found merged dataset files:")
            for f in merged_csv:
                print(f"   - {f}")
        else:
            print(f"\n⚠️  No 'Merged_dataset.csv' found")
            if csv_files or parquet_files:
                print(f"   Will need to merge individual files")
            else:
                print(f"   No data files found in container")
        
        if folders:
            print(f"\n📁 Folder structure:")
            for folder in sorted(list(folders))[:15]:
                print(f"   - {folder}/")
            if len(folders) > 15:
                print(f"   ... and {len(folders) - 15} more folders")
        
        if other_files:
            print(f"\n📄 Other files:")
            for f in other_files[:10]:
                print(f"   - {f}")
            if len(other_files) > 10:
                print(f"   ... and {len(other_files) - 10} more")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_blob_structure()

