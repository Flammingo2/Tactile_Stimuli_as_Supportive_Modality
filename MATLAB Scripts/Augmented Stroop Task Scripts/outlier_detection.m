%% Function for IQR outlier detection regarding the reaction time
function [indices_outlier,number_outlier] = outlier_detection(data)
% Detects IQR outlier and returns their indices and number
data = data.reaction_time;
% Determine the outlier indices
outlier = isoutlier(data, 'quartiles');
 
% Find rows with outliers plus their amount
indices_outlier = find(outlier);
number_outlier = height(indices_outlier);

