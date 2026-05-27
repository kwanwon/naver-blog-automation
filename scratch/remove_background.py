import os
from PIL import Image

def make_transparent_by_floodfill(image_path, output_path):
    print(f"Processing: {os.path.basename(image_path)}")
    img = Image.open(image_path).convert("RGBA")
    
    # We want to make the white background transparent.
    # The background is at the corners. Let's do a floodfill from (0,0) or check pixels close to white.
    # Since the emblem itself has white parts (like the lion face text inside the shield, or the white text),
    # a simple color replacement would make the inner white elements transparent too, which we DON'T want.
    # So we must use a floodfill-like boundary approach, or a smart mask.
    # Let's write a python script that does:
    # 1. Floodfill from the corners to find the background white and make it transparent.
    # Since it's a shield or text, the background surrounds the emblem.
    # Let's use PIL's ImageDraw.floodfill or standard BFS to clear background.
    
    from PIL import ImageDraw
    
    width, height = img.size
    
    # Find all white pixels connected to corners
    # Let's target exactly the background.
    # We'll do a flood fill starting from (0, 0), (width-1, 0), (0, height-1), (width-1, height-1)
    # Background color is white: (255, 255, 255)
    # Let's allow a slight tolerance because of compression artifacts (e.g. 240-255).
    
    # To do it with tolerance, we can do a BFS manual floodfill.
    pixels = img.load()
    visited = set()
    
    # Queue for BFS
    queue = []
    
    # Add corners
    corners = [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1), (10, 10), (width-11, 10)]
    for c in corners:
        queue.append(c)
        visited.add(c)
        
    def is_white_like(color):
        r, g, b, a = color
        # White or very close to white
        return r > 220 and g > 220 and b > 220
        
    while queue:
        x, y = queue.pop(0)
        
        # Check current pixel
        current_color = pixels[x, y]
        if is_white_like(current_color):
            # Make it transparent
            pixels[x, y] = (0, 0, 0, 0)
            
            # Add neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        # Only propagate if it's white-like to prevent bleeding into dark colors
                        neighbor_color = pixels[nx, ny]
                        if is_white_like(neighbor_color):
                            queue.append((nx, ny))

    # Also clean up any isolated white pixels at the borders
    for x in range(width):
        for y in range(height):
            # If it's on the border and white, make transparent
            if x < 3 or x > width - 4 or y < 3 or y > height - 4:
                if is_white_like(pixels[x, y]):
                    pixels[x, y] = (0, 0, 0, 0)

    img.save(output_path, "PNG")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    emblem1 = "/Users/gm2hapkido/Desktop/체육관엠블럼/KakaoTalk_Photo_2026-05-26-10-48-34.png"
    emblem2 = "/Users/gm2hapkido/Desktop/체육관엠블럼/KakaoTalk_Photo_2026-05-26-10-48-46.png"
    
    make_transparent_by_floodfill(emblem1, "/Users/gm2hapkido/Desktop/체육관엠블럼/엠블럼_투명.png")
    make_transparent_by_floodfill(emblem2, "/Users/gm2hapkido/Desktop/체육관엠블럼/사자만_투명.png")
