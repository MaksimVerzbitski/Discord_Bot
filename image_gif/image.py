from PIL import Image, ImageEnhance, ImageDraw
import os

# Load the images
img1 = Image.open("img/1.png")
img2 = Image.open("img/2.png")
img3 = Image.open("img/3.png")

# Resize images to be the same size (smallest dimension of any image to keep aspect ratio)
min_width = min(img1.width, img2.width, img3.width)
min_height = min(img1.height, img2.height)

img1 = img1.resize((min_width, min_height))
img2 = img2.resize((min_width, min_height))
img3 = img3.resize((min_width, min_height))

# Create a blank canvas for the grid
grid_width = min_width * 4
grid_height = min_height * 4
grid_image = Image.new('RGB', (grid_width, grid_height))

# Paste images into the grid
grid_image.paste(img1, (0, 0))
grid_image.paste(img2, (min_width, 0))
grid_image.paste(img3, (min_width * 2, 0))
grid_image.paste(img1, (min_width * 3, 0))
grid_image.paste(img2, (0, min_height))
grid_image.paste(img3, (min_width, min_height))
grid_image.paste(img1, (min_width * 2, min_height))
grid_image.paste(img2, (min_width * 3, min_height))
grid_image.paste(img3, (0, min_height * 2))
grid_image.paste(img1, (min_width, min_height * 2))
grid_image.paste(img2, (min_width * 2, min_height * 2))
grid_image.paste(img3, (min_width * 3, min_height * 2))
grid_image.paste(img1, (0, min_height * 3))
grid_image.paste(img2, (min_width, min_height * 3))
grid_image.paste(img3, (min_width * 2, min_height * 3))
grid_image.paste(img1, (min_width * 3, min_height * 3))

# Save the grid image
grid_image_path = "D:\\Projects\\Discord_Music\\image_gif\\grid_image_4.png"
grid_image.save(grid_image_path)

# Function to crop and process frames
def process_frames(grid_image, rows, cols, crop_pct=0.05, upscale_factor=1.01):
    frames = []
    frame_width = grid_image.width // cols
    frame_height = grid_image.height // rows

    for row in range(rows):
        for col in range(cols):
            left = col * frame_width
            upper = row * frame_height
            right = left + frame_width
            lower = upper + frame_height
            frame = grid_image.crop((left, upper, right, lower))
            
            # Crop the frame by 5% on all sides
            crop_x = int(frame_width * crop_pct)
            crop_y = int(frame_height * crop_pct)
            frame = frame.crop((crop_x, crop_y, frame_width - crop_x, frame_height - crop_y))
            
            # Upscale the frame
            frame = frame.resize((int(frame.width * upscale_factor), int(frame.height * upscale_factor)))
            
            frames.append(frame)
    return frames

# Function to add flashy lightning effects to frames
def add_flashy_effects(frames):
    flashy_frames = []
    for color in ["yellow", "white", "red"]:
        for frame in frames:
            flashy_frame = frame.copy()
            overlay = Image.new('RGB', flashy_frame.size, color)
            flashy_frame = Image.blend(flashy_frame, overlay, 0.5)
            flashy_frames.append(flashy_frame)
    return flashy_frames

# Function to create and save GIF with different durations
def create_gif(frames, slow_duration, fast_duration, output_path):
    # Calculate the number of frames for each duration
    num_slow_frames = len(frames) // 2
    num_fast_frames = len(frames) - num_slow_frames
    
    # Set up durations: first half slow, second half fast
    durations = [slow_duration] * num_slow_frames + [fast_duration] * num_fast_frames
    frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=durations, loop=0)

# Load the grid image
grid_image = Image.open(grid_image_path)

# Process the frames from the grid
rows, cols = 4, 4
processed_frames = process_frames(grid_image, rows, cols)

# Add flashy lightning effects to the first three frames
flashy_frames = add_flashy_effects(processed_frames[:3])

# Combine flashy frames with the rest of the processed frames
combined_frames = flashy_frames + processed_frames

# Create the GIF with slow then super flashy fast durations
gif_output_path = "D:\\Projects\\Discord_Music\\image_gif\\transformation_4.gif"
create_gif(combined_frames, slow_duration=500, fast_duration=50, output_path=gif_output_path)

print(f"GIF created successfully! You can find it here: {gif_output_path}")
