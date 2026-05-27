import sys
from rembg import remove
from PIL import Image

def process_emblem(input_path, output_path):
    print(f"Removing background from {input_path} using rembg...")
    try:
        input_image = Image.open(input_path)
        
        # remove background
        output_image = remove(input_image)
        
        output_image.save(output_path, "PNG")
        print(f"Successfully saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python use_rembg.py <input> <output>")
        sys.exit(1)
    
    process_emblem(sys.argv[1], sys.argv[2])
