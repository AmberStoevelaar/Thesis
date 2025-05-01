## Instructions
### Adding excel data
1. Add a folder with the name of the school to the `data/raw_data` folder
2. Add a single excel file to the folder

### Preprocessing data
To preprocess the data, follow these steps:
1. Open the `data/preprocess.py` file
2. Make sure the paths to the raw data and processed data are correct
   - `raw_data_path = "data/raw_data"`
   - `processed_data_path = "data/processed_data"`
3. Run `python3 code/preprocessing/preprocess.py` to preprocess the data for all schools

### Running optimization models
1. Open the `main.py` file
2. Make sure the paths to the processed data are correct
   - `processed_data_path = "data/processed_data"`
3. Run `python3 main.py <school> <method: cp|milp|random> [random_seed]`
   - `<school>`: The name of the school folder (e.g. `school1`)
   - `<method>`: The optimization method to use (e.g. `cp`, `milp`, `random`)
   - `[random_seed]`: Optional random seed for reproducibility (default is 42)



