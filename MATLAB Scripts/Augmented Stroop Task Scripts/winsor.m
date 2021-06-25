%% Winsorizing
% Input: Data vector of data to be winsorized, percentiles p
% [left_percentile, right_percentile]
function [data, number_outlier] = winsor(data, p)
% Get borders in data of 1st and 3rd quartile
p = prctile(data.reaction_time,p);
% Calcultae Inter-Quartile Range
iqr = p(2)-p(1);
% Calculate borders (1,5IQR)
p = [(p(1)- (1.5 * iqr)), (p(2)+ (1.5*iqr))];

% Determine outliers lower than border
outlier_left = data.reaction_time < p(1); 
% Get lowest value that is no outlier
value_leftborder = min(data.reaction_time(~outlier_left));
% Determine outliers higher than border
outlier_right = data.reaction_time > p(2);
% Get highest value that is no outlier
value_rightborder = max(data.reaction_time(~outlier_right));

% Replace all outliers with highest or lowest value that is no outlier
data{outlier_left,'reaction_time'} = value_leftborder;
data{outlier_right,'reaction_time'} = value_rightborder;

% Get number of outliers
tab1 = tabulate(outlier_left);
tab2 = tabulate(outlier_right);
number_outlier = height(outlier_left)- tab1{1,2} + height(outlier_right)- tab2{1,2};