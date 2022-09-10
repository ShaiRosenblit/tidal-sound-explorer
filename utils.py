import pandas as pd


def load_df():
    df = pd.read_csv('/Users/shai/Documents/tidal/segments220910.csv')
    df = df.rename(columns={'Unnamed: 0': 'seg_number_in_sample'})
    df['s'] = df.seg_sound.str.split(':').str[0]
    df['n'] = df.seg_sound.str.split(':').str[1].astype(int)
    df['col_x'] = df['pca_0']
    df['col_y'] = df['pca_1']
    df['col_x'] = scale_col(df['col_x'])
    df['col_y'] = scale_col(df['col_y'])
    df['color'] = df['cluster']
    df['point_size'] = 1
    return df


def scale_col(col: pd.Series):
    col = col + abs(col.min())
    col = col / col.max()
    return col
