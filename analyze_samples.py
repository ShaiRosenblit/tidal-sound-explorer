import pandas as pd
from path import Path
from tqdm import tqdm
import numpy as np
import librosa
from librosa.feature.spectral import mfcc, spectral_bandwidth, spectral_centroid, \
    spectral_contrast, spectral_flatness, spectral_rolloff
import umap
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from joblib import Parallel, delayed
import sklearn.cluster as cluster


def analyze_seg(samples, fs):
    samples = samples - np.mean(samples)

    feats = dict()
    feats['rms'] = np.mean(samples ** 2) ** 0.5
    mfcc_mat = mfcc(y=samples, sr=fs, n_mfcc=20)
    for i, v in enumerate(mfcc_mat.mean(axis=1)):
        feats[f'mfcc_{i}'] = v
    feats['spectral_bandwidth'] = np.mean(spectral_bandwidth(y=samples, sr=fs))
    feats['spectral_centroid'] = np.mean(spectral_centroid(y=samples, sr=fs))
    feats['spectral_contrast'] = np.mean(spectral_contrast(y=samples, sr=fs))
    feats['spectral_flatness'] = np.mean(spectral_flatness(y=samples))
    feats['spectral_rolloff'] = np.mean(spectral_rolloff(y=samples, sr=fs))
    feats['spectral_bandwidth_std'] = np.std(spectral_bandwidth(y=samples, sr=fs))
    feats['spectral_centroid_std'] = np.std(spectral_centroid(y=samples, sr=fs))
    feats['spectral_contrast_std'] = np.std(spectral_contrast(y=samples, sr=fs))
    feats['spectral_flatness_std'] = np.std(spectral_flatness(y=samples))
    feats['spectral_rolloff_std'] = np.std(spectral_rolloff(y=samples, sr=fs))
    s = pd.Series(samples)
    window = int(fs / 50)
    amp_env = (
        s
            .rolling(window).max()
            .shift(-window)
    )
    max_amp = amp_env.max()
    attack_thresh = max_amp * 0.9
    attack_idx = np.where(samples > attack_thresh)[0][0]
    attack_time = attack_idx / fs
    decay_val = max_amp * 0.10
    decay_idx = np.argmin(np.abs(amp_env[attack_idx:] - decay_val)) + attack_idx
    decay_time = decay_idx / fs
    feats['decay_dur'] = decay_time - attack_time
    feats['attack_dur'] = attack_time
    zero_crossing_idx = ((s < 0) & (s.shift(-1) > 0)) | ((s > 0) & (s.shift(-1) < 0))
    feats['zcr'] = zero_crossing_idx.mean() * fs
    feats['zcr_attack'] = zero_crossing_idx[:attack_idx].mean() * fs
    feats['zcr_decay'] = zero_crossing_idx[attack_idx:decay_idx].mean() * fs
    feats['rms_attack'] = (s[:attack_idx] ** 2).mean() ** 0.5
    feats['rms_decay'] = (s[attack_idx:decay_idx] ** 2).mean() ** 0.5
    return feats


def segment_and_analyze_sample(audio_file: Path, sound_name, min_seg_num_samples=2048):
    samples, fs = librosa.load(audio_file)
    track_dur = len(samples) / fs
    len_samples = len(samples)
    if track_dur > 1:
        onsets_idx = librosa.onset.onset_detect(y=samples, sr=fs, backtrack=True, units='samples')
    else:
        onsets_idx = [0, len_samples]
    segments_df = pd.DataFrame({'seg_start_idx': onsets_idx[:-1], 'seg_end_idx': onsets_idx[1:]})

    segments_df['seg_num_samples'] = segments_df['seg_end_idx'] - segments_df['seg_start_idx']
    segments_df = segments_df[segments_df.seg_num_samples > min_seg_num_samples]
    segments_df['seg_start'] = segments_df['seg_start_idx'] / len_samples
    segments_df['seg_end'] = segments_df['seg_end_idx'] / len_samples

    segments_df['seg_start_sec'] = segments_df['seg_start'] * track_dur
    segments_df['seg_end_sec'] = segments_df['seg_end'] * track_dur
    segments_df['seg_dur_sec'] = segments_df['seg_end_sec'] - segments_df['seg_start_sec']
    segments_df['full_sample_dur_sec'] = track_dur
    feats_list = []
    for i, r in segments_df.iterrows():
        try:
            feats = analyze_seg(samples[int(r.seg_start_idx):int(r.seg_end_idx)], fs)
        except Exception as e:
            print(f"failed to extrcat features to {sound_name}, segment {i}, {r['seg_dur_sec']}")
            raise e
        feats_list.append(feats)
    feats_df = pd.DataFrame(feats_list)
    segments_df['path'] = audio_file
    segments_df = pd.concat([segments_df, feats_df], axis=1)
    segments_df["seg_sound"] = sound_name
    if sum(segments_df.seg_dur_sec == 0) > 0:
        print('oh no')
    return segments_df


def gen_haskell_code(segments_df, haskell_file_path):
    print(segments_df)
    haskell_code_str_ln = ["let"]
    seg_sound_str = '", "'.join(segments_df.seg_sound.values)
    haskell_code_str_ln.append(f'\t\tseg_sound = ["{seg_sound_str}"]')
    seg_start_str = ', '.join(segments_df.seg_start.astype(str).values)
    haskell_code_str_ln.append(f'\t\tseg_start = [{seg_start_str}]')
    seg_end_str = ', '.join(segments_df.seg_end.astype(str).values)
    haskell_code_str_ln.append(f'\t\tseg_end = [{seg_end_str}]')
    haskell_code_str_ln.append(
        f'\t\tselseg n = (|>| begin (fit 0 seg_start n))  . (|>| end (fit 0 seg_end n)) . (|>| s (fit 0 seg_sound n))')

    haskell_code_str = "\n".join(haskell_code_str_ln)

    print(haskell_code_str)
    with open(haskell_file_path, 'w') as f:
        f.write(haskell_code_str)


def gen_samples_dict(sounds_dir):
    print(sounds_dir)
    dirs = Path(sounds_dir).dirs()
    # print(dirs)
    samples_dict = {}
    for directory in dirs:
        files = directory.files()
        files.sort()
        # print('*'*20)
        files = [f for f in files if f.ext.lower() == '.wav']
        for i, file in enumerate(files):
            # print(file.split('/')[-1])
            samples_dict[f"{directory.split('/')[-1]}:{i}"] = file
    return samples_dict


def gen_samples_dict_multi(sounds_dirs_multi):
    samples_dict_milti = {}
    for sounds_dir in sounds_dirs_multi:
        samples_dict_milti.update(gen_samples_dict(sounds_dir))
    return samples_dict_milti


def gen_seg_df(samples_dict):
    seg_df_list = \
        Parallel(n_jobs=-1)(
            delayed(segment_and_analyze_sample)(sample_path, sound_name)
            for sound_name, sample_path in tqdm(samples_dict.items())
        )

    # for sound_name, sample_path in tqdm(samples_dict.items()):
    #     cur_df = segment_and_analyze_sample(sample_path)
    #     cur_df["seg_sound"] = sound_name
    #     seg_df_list.append(cur_df)
    seg_df = pd.concat(seg_df_list)
    seg_df = seg_df.fillna(0)
    seg_df = seg_df[seg_df.seg_dur_sec > 0]
    return seg_df


def add_embeddings(df):
    feats_cols = [
        'seg_dur_sec',
        'rms',
        'mfcc_0', 'mfcc_1', 'mfcc_2',
        'mfcc_3', 'mfcc_4', 'mfcc_5', 'mfcc_6', 'mfcc_7', 'mfcc_8', 'mfcc_9',
        'mfcc_10', 'mfcc_11', 'mfcc_12', 'mfcc_13', 'mfcc_14', 'mfcc_15',
        'mfcc_16', 'mfcc_17', 'mfcc_18', 'mfcc_19',
        'spectral_bandwidth', 'spectral_centroid', 'spectral_contrast', 'spectral_flatness', 'spectral_rolloff',
        'spectral_bandwidth_std', 'spectral_centroid_std', 'spectral_contrast_std', 'spectral_flatness_std',
        'spectral_rolloff_std',
        'decay_dur', 'attack_dur',
        'zcr',
        'zcr_attack',
        'zcr_decay',
        'rms_attack',
        'rms_decay',
    ]
    reducer = umap.UMAP(
        random_state=42,
        n_neighbors=30,
        min_dist=0.0,
        n_components=2,
    )
    sscaler = StandardScaler()
    reducer.fit(df[feats_cols])
    umap_embedding = reducer.transform(sscaler.fit_transform(df[feats_cols]))
    df[[f'umap_{i}' for i in range(umap_embedding.shape[1])]] = umap_embedding

    pca = PCA()
    sscaler = StandardScaler()
    pca_embedding = pca.fit_transform(sscaler.fit_transform(df[feats_cols]))
    df[[f'pca_{i}' for i in range(pca_embedding.shape[1])]] = pca_embedding
    df['cluster'] = cluster.KMeans(n_clusters=8).fit_predict(
        np.hstack([pca_embedding[:, :5]]))  # , umap_embedding[:, :0]]))

    return df


def main():
    samples_dict = gen_samples_dict_multi([
        '/Users/shai/Library/Application Support/SuperCollider/downloaded-quarks/Dirt-Samples',
        '/Users/shai/Documents/tidal/sounds/samples-yt',
        '/Users/shai/Documents/tidal/sounds/samples-extra',
    ])

    df = gen_seg_df(samples_dict)
    df = add_embeddings(df)
    df.to_csv('/Users/shai/Documents/tidal/segments220910.csv')
    # gen_haskell_code(df, '/Users/shai/Documents/tidal/segments.hs')


if __name__ == '__main__':
    main()
