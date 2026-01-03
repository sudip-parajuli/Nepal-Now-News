from abc import ABC, abstractmethod

class BasePipeline(ABC):
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    async def run(self):
        """
        Main execution logic for the pipeline.
        """
        pass

    def cleanup_storage(self):
        """
        Removes temporary media files from the storage directory.
        Keeps json and log files.
        """
        import os
        import glob
        
        storage_dir = "automation/storage"
        if not os.path.exists(storage_dir):
            return

        print(f"Cleaning up temporary files in {storage_dir}...")
        
        # Extensions to remove
        extensions = ['*.mp3', '*.mp4', '*.wav', '*.jpg', '*.png', '*.jpeg']
        files_to_remove = []
        
        for ext in extensions:
            files_to_remove.extend(glob.glob(os.path.join(storage_dir, ext)))
            
        for f in files_to_remove:
            try:
                # Don't delete "posted" json files or logs
                if "posted" in f or ".json" in f or ".log" in f:
                    continue
                    
                os.remove(f)
                # print(f"Deleted: {f}")
            except Exception as e:
                print(f"Error deleting {f}: {e}")
        
        # Also clean up the 'temp' directory used by Wav2Lip if it exists
        temp_dir = "temp"
        if os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
                # Re-create it empty for next run (or let lip_sync do it)
                # os.makedirs(temp_dir, exist_ok=True) 
            except Exception as e:
                print(f"Error cleaning temp dir: {e}")
