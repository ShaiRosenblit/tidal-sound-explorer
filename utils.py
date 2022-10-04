import pandas as pd

import config

def segment_csv_path():
    result = os.path.expanduser(config.segment_csv)
    try:
        os.makedirs(os.path.dirname(output_csv))
    except FileExistsError:
        # directory already exists
        pass
    return result

def load_df():
    df = pd.read_csv(segment_csv_path())
    df = df.rename(columns={'Unnamed: 0': 'seg_number_in_sample'})
    df['s'] = df.seg_sound.str.split(':').str[0]
    df['n'] = df.seg_sound.str.split(':').str[1].astype(int)
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            df[f"{c}_norm"] = scale_col(df[c])
            df[f"{c}_norm"] = scale_col(df[c])
    df['col_x'] = df['pca_1']
    df['col_y'] = df['pca_2']
    df['col_x'] = scale_col(df['col_x'])
    df['col_y'] = scale_col(df['col_y'])
    df['color'] = df['cluster']
    df['point_size'] = 1
    return df

def scale_col(col: pd.Series):
    col = col - col.min()
    col = col / col.max()
    return col
