"""Address completeness feature extractor.
Incomplete addresses are the single strongest RTO predictor in
Indian e-commerce. This transformer quantifies address quality
across 6 dimensions."""

import re
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Optional

HOUSE_NUM_PATTERN = re.compile(
    r'(flat|floor|house|h\.?no|hno|door|#|f-|f/|plot|door\s*no|d\.?no)',
    re.IGNORECASE
)
LANDMARK_PATTERN = re.compile(
    r'(near|behind|opposite|opp|beside|next\s*to|adj|adjacent|landmark|signal|temple|school|hospital|market|mall|metro)',
    re.IGNORECASE
)
DIGIT_PATTERN = re.compile(r'\d+')
AREA_PIN_PATTERN = re.compile(r'\b\d{6}\b')


class AddressCompletenessTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.feature_names_out_ = []

    def fit(self, X, y=None) -> "AddressCompletenessTransformer":
        self.feature_names_out_ = [
            "addr_char_len", "addr_word_count", "has_house_num",
            "has_landmark", "has_digit_token", "addr_completeness_score"
        ]
        return self

    def _extract_single(self, address: str) -> list:
        # Step 1: Safely convert to string
        if address is None or (isinstance(address, float) and np.isnan(address)):
            address_clean = ""
        else:
            address_clean = str(address).strip()

        if not address_clean:
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Step 2: Compute features
        addr_char_len = float(len(address_clean))
        addr_word_count = float(len(address_clean.split()))

        has_house_num = 1.0 if HOUSE_NUM_PATTERN.search(address_clean) else 0.0
        if has_house_num == 0.0:
            # Check for digit tokens of length <= 4
            digits = DIGIT_PATTERN.findall(address_clean)
            if any(len(d) <= 4 for d in digits):
                has_house_num = 1.0

        has_landmark = 1.0 if LANDMARK_PATTERN.search(address_clean) else 0.0
        has_digit_token = 1.0 if DIGIT_PATTERN.search(address_clean) else 0.0

        # Completeness score
        addr_completeness_score = (
            (0.30 * min(addr_char_len, 60) / 60.0) +
            (0.25 * min(addr_word_count, 10) / 10.0) +
            (0.25 * has_house_num) +
            (0.20 * has_landmark)
        )
        addr_completeness_score = min(1.0, max(0.0, addr_completeness_score))

        return [addr_char_len, addr_word_count, has_house_num, has_landmark, has_digit_token, addr_completeness_score]

    def transform(self, X, y=None) -> pd.DataFrame:
        # Handle different input types
        if isinstance(X, pd.DataFrame):
            addresses = X.get("address", X.iloc[:, 0] if len(X.columns) > 0 else [])
        elif isinstance(X, pd.Series):
            addresses = X
        else:
            addresses = X

        # Extract features for each address
        features_list = [self._extract_single(addr) for addr in addresses]

        # Return DataFrame
        df_features = pd.DataFrame(features_list, columns=self.feature_names_out_)
        return df_features.astype(np.float64)


if __name__ == "__main__":
    test_cases = [
        "123 Main St",
        None,
        "Flat 4B, 2nd Floor, Sunrise Apt, Near City Mall, Koramangala",
        "",
        "opp temple sector 15"
    ]
    t = AddressCompletenessTransformer()
    t.fit(None)
    df_test = pd.DataFrame({"address": test_cases})
    print(t.transform(df_test))
