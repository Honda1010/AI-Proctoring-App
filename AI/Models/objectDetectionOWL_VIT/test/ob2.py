import os
import cv2
import numpy as np
from PIL import Image
from transformers import pipeline

print("Loading OWL-ViT model...")
detector = pipeline(
    task="zero-shot-object-detection", 
    model="google/owlvit-base-patch32",
    device="cpu"
)

CHEATING_CLASSES = [
    "Mobile phone", "Earphone", "headset", "smart watch", "sunglasses", "cap"
]

INPUT_FOLDER = "test_images"  
OUTPUT_FOLDER = "output_images" 

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

if not os.path.exists(INPUT_FOLDER):
    print(f"Error: The folder '{INPUT_FOLDER}' does not exist. Please create it and add some images.")
    exit()

valid_extensions = (".jpg", ".jpeg", ".png")
image_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_extensions)]

if len(image_files) == 0:
    print(f"No images found in '{INPUT_FOLDER}'. Please add some .jpg or .png files.")
    exit()

print(f"Found {len(image_files)} images. Starting batch processing...\n")

for filename in image_files:
    image_path = os.path.join(INPUT_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, f"result_{filename}")
    
    print(f"Processing: {filename}")
    
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  -> Could not read {filename}. Skipping. Error: {e}")
        continue

    predictions = detector(
        image,
        candidate_labels=CHEATING_CLASSES,
    )
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    items_found = 0
    for prediction in predictions:
        if prediction["score"] > 0.1: 
            items_found += 1
            box = prediction["box"]
            label = prediction["label"]
            score = prediction["score"]
            
            xmin, ymin = box["xmin"], box["ymin"]
            xmax, ymax = box["xmax"], box["ymax"]
            
            cv2.rectangle(cv_image, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
            cv2.putText(cv_image, f"{label}: {score:.2f}", (xmin, ymin - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    success = cv2.imwrite(output_path, cv_image)
    if success:
        print(f"  -> Found {items_found} items. Saved to {OUTPUT_FOLDER}/result_{filename}")
    else:
        print(f"  -> Error: Could not save the image.")

print("\nBatch processing complete! Check the 'output_images' folder for your results.")

# import transformers; print(transformers.__version__)