# =============================================================================
# FRED-MD preprocessing
#
# Pipeline:
#   1. Load the vintage and apply the tcode transformations   (fbi::fredmd)
#   2. Remove outliers, setting them to NA                     (fbi::rm_outliers.fredmd)
#   3. Summarise missing values by decade (table + heatmap)
#   4. Impute missing values with the tall-wide method         (fbi::tw_apc)
#   5. Save transformed (with NAs) and imputed (clean) CSVs
#
# Run from the repo root (open the .Rproj), or rely on here() below.
# =============================================================================

library(fbi)
library(here)

# ---- Settings ---------------------------------------------------------------
VINTAGE   <- "2026-09"                     # change to the vintage the group agrees on
RAW_FILE  <- here("data", "raw", paste0(VINTAGE, "-MD.csv"))
KMAX      <- 8                             # max factors used inside the imputation
DATE_END  <- NULL                          # e.g. as.Date("2026-06-01") to drop a ragged final month

dir.create(here("data", "clean"), showWarnings = FALSE, recursive = TRUE)
dir.create(here("output"),        showWarnings = FALSE)
dir.create(here("figures"),       showWarnings = FALSE)

# ---- 1. Load and transform --------------------------------------------------
md <- fredmd(RAW_FILE, date_start = NULL, date_end = DATE_END, transform = TRUE)

# ---- 2. Outliers ------------------------------------------------------------
# McCracken & Ng rule: |x - median| > 10 * IQR  ->  set to NA
md_clean <- rm_outliers.fredmd(md)

# Plain data frame, and drop the first 2 rows lost to (second) differencing
md_clean <- as.data.frame(md_clean)
md_clean <- md_clean[-(1:2), ]

dates <- as.Date(md_clean$date)
X     <- as.matrix(md_clean[, -1])
rownames(X) <- format(dates)

n_outliers <- sum(is.na(X)) - sum(is.na(as.matrix(as.data.frame(md)[-(1:2), -1])))
cat("Dimensions (T x N):", dim(X), "\n")
cat("Sample:", format(min(dates)), "to", format(max(dates)), "\n")
cat("Outliers set to NA:", n_outliers, "\n")

# ---- 3. Missing values by decade ---------------------------------------------
decade  <- (as.integer(format(dates, "%Y")) %/% 10) * 10
has_na  <- colSums(is.na(X)) > 0

miss_by_decade <- t(rowsum(is.na(X[, has_na, drop = FALSE]) * 1, decade))
miss_by_decade <- miss_by_decade[order(-rowSums(miss_by_decade)), , drop = FALSE]
print(miss_by_decade)
write.csv(miss_by_decade, here("output", "missing_by_decade.csv"))

# Share of all cells missing, per decade
pct_missing <- round(100 * tapply(rowSums(is.na(X)), decade, sum) /
                       (table(decade) * ncol(X)), 2)
cat("\n% of cells missing by decade:\n"); print(pct_missing)

cat("\nComplete months:", sum(rowSums(is.na(X)) == 0),
    " Complete series:", sum(colSums(is.na(X)) == 0), "\n")

# Heatmap: only series with any missing values, most-missing at the top
na_mat <- is.na(X[, has_na, drop = FALSE]) * 1
na_mat <- na_mat[, order(colSums(na_mat)), drop = FALSE]
decade_starts <- as.Date(paste0(seq(1960, 2020, by = 10), "-01-01"))

png(here("figures", "missing_heatmap.png"), width = 1600, height = 900, res = 130)
par(mar = c(3, 10, 3, 1))
image(x = as.numeric(dates), y = seq_len(ncol(na_mat)), z = na_mat,
      col = c("grey95", "firebrick"), axes = FALSE, xlab = "", ylab = "",
      main = paste0("FRED-MD missing values after outlier removal (", VINTAGE, ")"))
axis(1, at = as.numeric(decade_starts), labels = format(decade_starts, "%Y"))
axis(2, at = seq_len(ncol(na_mat)), labels = colnames(na_mat), las = 1, cex.axis = 0.6)
abline(v = as.numeric(decade_starts), col = "grey60", lty = 3)
dev.off()

# ---- 4. Tall-wide imputation ------------------------------------------------
# center + standardize so units don't drive the factors;
# tw_apc returns $data on the ORIGINAL scale with only the gaps filled.
imp      <- tw_apc(X, kmax = KMAX, center = TRUE, standardize = TRUE, re_estimate = TRUE)
X_filled <- imp$data

# Sanity checks
stopifnot(!anyNA(X_filled))
stopifnot(isTRUE(all.equal(X_filled[!is.na(X)], X[!is.na(X)])))   # observed values untouched
cat("Imputed cells:", sum(is.na(X)), "\n")

# ---- 5. Save ----------------------------------------------------------------
# Transformed with NAs: for anyone who wants to impute inside forecast windows
write.csv(data.frame(date = dates, X, check.names = FALSE),
          here("data", "clean", paste0("fredmd_transformed_", VINTAGE, ".csv")),
          row.names = FALSE)

# Fully imputed: ready for PCA / forecasting in Python
write.csv(data.frame(date = dates, X_filled, check.names = FALSE),
          here("data", "clean", paste0("fredmd_clean_", VINTAGE, ".csv")),
          row.names = FALSE)

cat("Done.\n")