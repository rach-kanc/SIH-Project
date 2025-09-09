# Plant Disease Identifier



**Goal:** Create an Image classifier model that can identify plant diseases based on an image of a leaf provided by the user (but the model works only for bell pepper, potato and tomato plants)



**Dataset:** PlantVillage Dataset (link: https://www.kaggle.com/datasets/emmarex/plantdisease)



## Repo structure

- notebooks/: Preprocessing the data and training the model

- src/: reusable modules (data.py, train.py, model.py, predict.py)

- app/: Streamlit demo

- experiments/: final model and artifacts



## Model

-The trained model's state dictionary is saved as experiments/PlantDiseaseIdentifier.pth . 

-The model was trained using data augmentation and transfer learning.

-The base model is EfficientNet-B1 trained on the ImageNet dataset before training it on our dataset.



## How to run locally

1. Create venv and install requirements

2. `jupyter notebook`

3. `streamlit run streamlit_app.py`



## Notes
- Because the dataset is big it won't be added to the repo, it's gonna be up to you to download it from the link provided and you need to create the folders **data** and **PlantVillage** (image_classifier_explainability/data/PlantVillage) and store the dataset inside the PlantVillage directory.

- Only the model's state dictionary is saved after running the notebook.

- To reproduce the model: run `notebooks/PlantDiseaseIdentifier.ipynb` end-to-end (it produces experiments/PlantDiseaseIdentifier.pth).



## Live Demo

- URL: https://plantdiseaseidentifier-7gtdeyaxg8uwbj4qgvtf6f.streamlit.app/


## License

- Unknown



## Author

- Khalil Fawaz — link to LinkedIn: www.linkedin.com/in/khalil-fawaz-aa7709314



