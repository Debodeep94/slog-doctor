import pandas as pd
from sklearn.model_selection import train_test_split

# Load your dataframe with CheXpert labels
df = pd.read_csv("/Users/debodeepbanerjee/Library/CloudStorage/OneDrive-Personal/Documents/r2gen/chexpert_labeler/chexpert_eval/R2GenCMN/010425/0.01_with_paths.csv")
elim_studies = ['s55265250', 's52440373', 's54527138', 's58001075', 's58214761', 
                's58144724', 's58929044', 's59507972', 's59083645', 's56264253', 
                's54240852', 's59891116', 's53091413', 's58510466', 's55372843', 
                's51096107', 's53183813', 's50255843', 's55743226', 's58274962', 
                's56443683', 's54780158', 's53417168', 's53850317', 's58598132', 
                's52667466', 's59698565', 's52124829', 's54472974', 's56241369']

df = df[~df['study_id'].isin(elim_studies)]
print(df)
labels = ["Atelectasis", "Cardiomegaly", "Consolidation", "Edema",
          "Enlarged Cardiomediastinum", "Fracture", "Lung Lesion", "Lung Opacity",
          "Pleural Effusion", "Pleural Other", "Pneumonia", "Pneumothorax",
          "Support Devices", "No Finding"]

selected = []

# Step 1: Ensure at least 2 positives per class
for label in labels:
    pos_cases = df[df[label] == 1]
    if len(pos_cases) >= 2:
        selected.append(pos_cases.sample(2, random_state=42))
    elif len(pos_cases) > 0:  # if very rare
        selected.append(pos_cases.sample(len(pos_cases), random_state=42))

selected_df = pd.concat(selected).drop_duplicates()

# Step 2: If fewer than 25, add random extra samples
if len(selected_df) < 25:
    remaining = df.drop(selected_df.index)
    extra = remaining.sample(25 - len(selected_df), random_state=42)
    selected_df = pd.concat([selected_df, extra])

# Step 3: Trim if too many
if len(selected_df) > 25:
    selected_df = selected_df.sample(25, random_state=42)

print(selected_df.shape)
selected_df.to_csv("/Users/debodeepbanerjee/Library/CloudStorage/OneDrive-Personal/Documents/r2gen/chexpert_labeler/chexpert_eval/R2GenCMN/010425/selected_samples_new.csv", index=False)

candidate_subj = selected_df['study_id'].unique()
df_00 = pd.read_csv("/Users/debodeepbanerjee/Library/CloudStorage/OneDrive-Personal/Documents/r2gen/chexpert_labeler/chexpert_eval/R2GenCMN/010425/0.0_with_paths.csv")
selected_df_00 = df_00[df_00['study_id'].isin(candidate_subj)]
print(df_00.shape)
selected_df_00.to_csv("/Users/debodeepbanerjee/Library/CloudStorage/OneDrive-Personal/Documents/r2gen/chexpert_labeler/chexpert_eval/R2GenCMN/010425/selected_samples_00_new.csv", index=False)
