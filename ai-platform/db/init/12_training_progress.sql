-- Lets the frontend show a live "epoch X/Y" percentage while a training_job
-- is running, instead of just a static "running" status with no ETA.
USE ai_training;
GO

IF COL_LENGTH('training_job', 'progress_current_epoch') IS NULL
BEGIN
    ALTER TABLE training_job ADD progress_current_epoch INT NULL;
END
GO

IF COL_LENGTH('training_job', 'progress_total_epochs') IS NULL
BEGIN
    ALTER TABLE training_job ADD progress_total_epochs INT NULL;
END
GO
