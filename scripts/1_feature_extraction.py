import cv2
import numpy as np
import os
import re
from tqdm import tqdm  # Progress bar
import pandas as pd
import mahotas as mh
from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
from radiomics import featureextractor
import SimpleITK as sitk

# 📌 Root directory containing all experiments
root_dir = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D"

# Timepoints and replicates
timepoints = ["72H", "96H", "120H"]
replicates = ["R1", "R2", "R3"]
cell_lines = ["BT549", "HCC1806", "MDA468"]

# List to collect base_dirs
base_dirs = []

# Traverse all expected combinations
for tp in timepoints:
    for rep in replicates:
        current_path = os.path.join(root_dir, tp, rep)
        if not os.path.exists(current_path):
            continue
        for folder in os.listdir(current_path):
            full_path = os.path.join(current_path, folder)
            if os.path.isdir(full_path) and any(line in folder for line in cell_lines):
                base_dirs.append(full_path)

# Optional: check number of directories found
print(f"✅ Found {len(base_dirs)} experimental folders for processing.")


# ==============================================================================
#                               CONFIGURATION - PATHS
# ==============================================================================

# Loop over each base_dir
for base_dir in base_dirs:
    try:
        print(f"\n🚀 Processing: {base_dir}")

        # Generate experiment ID (e.g., 72H_R1_BT549)
        experiment_id = base_dir.replace(root_dir, "").strip("\\").replace("\\", "_")

        # Define paths
        images_dir = os.path.join(base_dir, "Images")
        mip_dir = os.path.join(images_dir, "1. MIP")
        mip8_dir = os.path.join(images_dir, "2. MIP8bits")
        contours_dir = os.path.join(images_dir, "3. Contours")
        spheroids_dir = os.path.join(images_dir, "4. Spheroids")
        features_xlsx = os.path.join(base_dir, "spheroid_features.xlsx")
        clusters_xlsx = os.path.join(base_dir, "spheroid_clusters.xlsx")

        # Ensure output folders exist
        for folder in [mip_dir, mip8_dir, contours_dir, spheroids_dir]:
            os.makedirs(folder, exist_ok=True)


        # ==============================================================================
        #                  MAXIMUM INTENSITY PROJECTION (16-bit)
        # ==============================================================================

        # Regex to identify and group image files by base name (rXXcXXfXX)
        pattern = re.compile(r"(r\d{2}c\d{2}f\d{2})p(01|02|03|04)-ch\d+sk\d+fk\d+fl\d+\.tiff$", re.IGNORECASE)

        # Dictionary to group files by image ID (without plane identifier)
        image_groups = {}

        # Scan Z-stack image folder
        for file in os.listdir(images_dir):
            match = pattern.match(file)
            if match:
                base_name = match.group(1)  # Unique image ID without pXX
                if base_name not in image_groups:
                    image_groups[base_name] = []
                image_groups[base_name].append(os.path.join(images_dir, file))

        # Total number of projections to process
        total_images = len(image_groups)
        print(f"🔄 Generating maximum intensity projections for {total_images} image stacks...")

        # Process each group using a progress bar
        with tqdm(total=total_images, desc="Generating MIP", unit="img") as pbar:
            for base_name, file_list in image_groups.items():
                file_list.sort()  # Ensure planes are ordered correctly

                # Load planes into a 3D array
                stack_images = []
                for file_path in file_list:
                    img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        print(f"⚠️ Failed to read: {file_path}")
                        continue
                    if img.dtype != np.uint16:
                        print(f"⚠️ Warning: {file_path} is not 16-bit ({img.dtype}).")
                    stack_images.append(img)

                if len(stack_images) == 0:
                    print(f"⚠️ No valid planes found for {base_name}.")
                    pbar.update(1)
                    continue

                # Convert to numpy array (z, h, w)
                stack_images = np.array(stack_images, dtype=np.uint16)

                # Apply maximum intensity projection
                mip_image = np.max(stack_images, axis=0)

                # Save 16-bit projection
                output_path = os.path.join(mip_dir, f"{base_name}_MIP.tiff")
                cv2.imwrite(output_path, mip_image)

                # Update progress bar
                pbar.update(1)

        print(f"\n✅ MIP generation completed. Files saved in: {mip_dir}")


        # =======================================================================================
        #                       CONVERT MIP IMAGES TO 8-BIT FORMAT
        # =======================================================================================

        # List all TIFF files in the 16-bit MIP directory
        image_files = [f for f in os.listdir(mip_dir) if f.lower().endswith(".tiff")]

        print(f"🔄 Converting {len(image_files)} MIP images to 8-bit...")

        # Process each 16-bit image and convert to 8-bit
        for image_file in tqdm(image_files, desc="Converting to 8-bit", unit="img"):
            image_path = os.path.join(mip_dir, image_file)

            # Read 16-bit image
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

            if img is None:
                print(f"⚠️ Could not read {image_file}, skipping.")
                continue

            # Percentile clipping to avoid extreme values
            p1, p99 = np.percentile(img, (1, 99))
            img_clipped = np.clip(img, p1, p99)

            # Normalize to 8-bit
            img_8bit = cv2.normalize(img_clipped, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

            # Save the 8-bit image
            output_path = os.path.join(mip8_dir, image_file)
            cv2.imwrite(output_path, img_8bit)

        print(f"\n✅ All 8-bit MIP images saved in: {mip8_dir}")

        #=======================================================================================
        #                       DETECT CONTOURS ON 8-BIT MIP IMAGES
        #=======================================================================================

        # List all TIFF files in the 8-bit MIP directory
        image_files = [f for f in os.listdir(mip8_dir) if f.lower().endswith(".tiff")]

        print(f"🔍 Processing {len(image_files)} images to detect spheroid contours...\n")

        # Process each image to detect contours
        for image_file in tqdm(image_files, desc="Detecting contours", unit="img"):
            image_path = os.path.join(mip8_dir, image_file)

            # Load grayscale image
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(img, (5, 5), 0)

            # Apply adaptive thresholding (Otsu) to detect darker spheroids
            _, binary_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Morphological filtering to remove small artifacts
            kernel = np.ones((3, 3), np.uint8)
            binary_clean = cv2.morphologyEx(binary_otsu, cv2.MORPH_OPEN, kernel, iterations=2)

            # Find external contours
            contours, _ = cv2.findContours(binary_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Convert image to BGR to draw colored contours
            img_contours = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # Draw contours in green
            cv2.drawContours(img_contours, contours, -1, (0, 255, 0), 2)

            # Save image with contours
            output_path = os.path.join(contours_dir, image_file)
            cv2.imwrite(output_path, img_contours)

        print(f"\n📁 Contour detection completed. Files saved in: {contours_dir}")


        # ==============================================================================
        #        SELECT AND DRAW ONLY THE LARGEST SPHEROID CONTOUR PER IMAGE
        # ==============================================================================

        print(f"🔍 Processing {len(image_files)} images to extract the largest spheroid...\n")

        # Loop through each image to isolate the largest contour
        for image_file in tqdm(image_files, desc="Drawing largest spheroid", unit="img"):
            image_path = os.path.join(contours_dir, image_file)

            # Load grayscale version of the contour image
            img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

            # Convert to BGR for drawing
            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)

            # Otsu thresholding to binarize
            _, binary_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Morphological cleaning
            kernel = np.ones((3, 3), np.uint8)
            binary_clean = cv2.morphologyEx(binary_otsu, cv2.MORPH_OPEN, kernel, iterations=2)

            # Find external contours
            contours, _ = cv2.findContours(binary_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # If at least one contour is found
            if contours:
                # Select the largest contour based on area
                largest_contour = max(contours, key=cv2.contourArea)

                # Draw it in green
                cv2.drawContours(img_color, [largest_contour], -1, (0, 255, 0), thickness=2)

                # Save the result in the "4. Spheroids" folder
                output_path = os.path.join(spheroids_dir, image_file)
                cv2.imwrite(output_path, img_color)

        print(f"\n📁 Largest spheroid contours saved in: {spheroids_dir}")



        # ==============================================================================
        #                      FEATURE EXTRACTION - COMPLETE - RADIOMICS
        # ==============================================================================

        # Configure Pyradiomics feature extractor
        extractor = featureextractor.RadiomicsFeatureExtractor()
        extractor.enableAllFeatures()  # Enable ALL features

        # 📁 Directory with images containing the largest object contour
        image_files = [f for f in os.listdir(spheroids_dir) if f.endswith(".tiff")] if os.path.exists(spheroids_dir) else []

        # Store extracted features
        features_list = []

        # Progress bar
        with tqdm(total=len(image_files), desc="Extracting features", unit="img") as pbar:
            for image_file in image_files:
                image_path = os.path.join(spheroids_dir, image_file)

                # Load image in grayscale
                img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img_gray is None:
                    continue

                # Apply thresholding
                _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                # Find contours
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue

                # Select largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                perimeter = cv2.arcLength(largest_contour, True)

                # Shape descriptors
                circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
                hull = cv2.convexHull(largest_contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                x, y, w, h = cv2.boundingRect(largest_contour)
                bounding_box_area = w * h
                extent = area / bounding_box_area if bounding_box_area > 0 else 0

                # Ellipse fitting
                if len(largest_contour) >= 5:
                    ellipse = cv2.fitEllipse(largest_contour)
                    major_axis = max(ellipse[1])
                    minor_axis = min(ellipse[1])
                    aspect_ratio = major_axis / minor_axis if minor_axis > 0 else 0
                else:
                    major_axis = minor_axis = aspect_ratio = 0

                # Hu moments
                moments = cv2.moments(largest_contour)
                hu_moments = cv2.HuMoments(moments).flatten()

                # GLCM texture features
                glcm = graycomatrix(img_gray, [1], [0], 256, symmetric=True, normed=True)
                contrast = graycoprops(glcm, 'contrast')[0, 0]
                correlation = graycoprops(glcm, 'correlation')[0, 0]
                energy = graycoprops(glcm, 'energy')[0, 0]
                homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]

                # LBP (Local Binary Patterns)
                lbp = local_binary_pattern(img_gray, P=8, R=1, method="uniform")
                lbp_hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 11), density=True)

                # Haralick features (Mahotas)
                haralick_features = mh.features.haralick(img_gray).mean(axis=0)

                # Create binary mask from contour
                mask = np.zeros_like(img_gray)
                cv2.drawContours(mask, [largest_contour], -1, 1, thickness=cv2.FILLED)

                # Convert to SimpleITK images
                mask_sitk = sitk.GetImageFromArray(mask.astype(np.uint8))
                img_sitk = sitk.GetImageFromArray(img_gray.astype(np.uint8))  # or uint16 if needed

                # Save temporary mask
                mask_path = os.path.join(spheroids_dir, "mask.png")
                sitk.WriteImage(mask_sitk, mask_path)

                # Radiomics feature extraction
                pyradiomics_features = extractor.execute(img_sitk, mask_sitk)
                pyradiomics_values = list(pyradiomics_features.values())[1:]  # Skip first (file name)

                # Combine all features
                features_list.append([
                    image_file, area, perimeter, circularity, solidity, extent,
                    major_axis, minor_axis, aspect_ratio, *hu_moments,
                    contrast, correlation, energy, homogeneity,
                    *lbp_hist, *haralick_features, *pyradiomics_values
                ])

                pbar.update(1)

        # Column names
        column_names = [
            "Filename", "Area", "Perimeter", "Circularity", "Solidity", "Extent",
            "MajorAxis", "MinorAxis", "AspectRatio",
            "Hu1", "Hu2", "Hu3", "Hu4", "Hu5", "Hu6", "Hu7",
            "GLCM_Contrast", "GLCM_Correlation", "GLCM_Energy", "GLCM_Homogeneity",
            "LBP_0", "LBP_1", "LBP_2", "LBP_3", "LBP_4", "LBP_5", "LBP_6", "LBP_7", "LBP_8", "LBP_9",
            "Haralick_1", "Haralick_2", "Haralick_3", "Haralick_4", "Haralick_5", "Haralick_6",
            "Haralick_7", "Haralick_8", "Haralick_9", "Haralick_10", "Haralick_11", "Haralick_12", "Haralick_13"
        ]

        # Add Pyradiomics feature names
        pyradiomics_column_names = list(pyradiomics_features.keys())[1:]
        column_names.extend(pyradiomics_column_names)

        # Create DataFrame
        df_features = pd.DataFrame(features_list, columns=column_names)

        # Save to Excel
        df_features.to_excel(features_xlsx, index=False, engine="openpyxl")
        print(f"✅ Feature table saved to: {features_xlsx}")

        # Optional: preview
        df_features.head()


    except Exception as e:
        print(f"❌ Error processing {base_dir}: {e}")
