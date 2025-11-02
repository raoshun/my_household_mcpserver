"""サードパーティの非推奨警告（テストで制御できないもの）を抑制します。"""

import warnings

warnings.filterwarnings(
    "ignore",
    message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated",
    category=DeprecationWarning,
)
