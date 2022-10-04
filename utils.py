import pandas as pd
import numpy as np

import config
import os

def segment_csv_path():
    result = os.path.expanduser(config.segment_csv)
    try:
        os.makedirs(os.path.dirname(result))
    except FileExistsError:
        # directory already exists
        pass
    return result

def load_df():
    df = pd.read_csv(segment_csv_path())
    df = df.rename(columns={'Unnamed: 0': 'seg_number_in_sample'})
    newcols = dict()
    newcols['s'] = df.seg_sound.str.split(':').str[0]
    newcols['n'] = df.seg_sound.str.split(':').str[1].astype(int)
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            newcols[f"{c}_norm"] = scale_col(df[c])
            newcols[f"{c}_percentile"] = df[c].argsort().argsort() / len(df)
    newcols['col_x'] = df['pca_0']
    newcols['col_y'] = df['pca_1']
    newcols['col_x'] = scale_col(newcols['col_x'])
    newcols['col_y'] = scale_col(newcols['col_y'])
    newcols['color'] = df['cluster']
    newcols['point_size'] = 1
    df = pd.concat([df, pd.DataFrame(newcols, index=df.index)], axis=1)
    return df


def scale_col(col: pd.Series):
    col = col - col.min()
    col = col / col.max()
    return col
