import zipfile
import os
import glob

def check_docx_images():
    docx_files = glob.glob("exports/*NotebookLM*.docx")
    if not docx_files:
        print("No matching docx found.")
        return

    target = docx_files[0]
    print(f"Checking: {target} ({os.path.getsize(target)} bytes)")
    
    try:
        with zipfile.ZipFile(target, 'r') as z:
            images = [f for f in z.namelist() if f.startswith('word/media/')]
            print(f"Found {len(images)} images in docx.")
            for img in images:
                info = z.getinfo(img)
                print(f"  - {img}: {info.file_size} bytes")
                
            if not images:
                print("WARNING: No images found inside docx!")
            else:
                total_img_size = sum(z.getinfo(i).file_size for i in images)
                print(f"Total image size: {total_img_size} bytes")

                # Check document.xml for text content size
                doc_xml = z.getinfo('word/document.xml')
                print(f"Document text XML size: {doc_xml.file_size} bytes")

    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == "__main__":
    check_docx_images()
