-- Lets a dataset import only filter matching filenames from a recursively
-- scanned folder (e.g. only "*Stitch_Img*" out of a folder mixing many
-- per-camera capture variants) instead of ingesting every image found.
USE ai_dataset;
GO

IF COL_LENGTH('dataset', 'filename_pattern') IS NULL
BEGIN
    ALTER TABLE dataset ADD filename_pattern NVARCHAR(200) NULL;
END
GO
