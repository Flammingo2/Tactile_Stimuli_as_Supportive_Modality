function [indices_outlier,number_outlier] = outlier_detection(data)
%detects IQR outlier and deletes rows
global variable_in_question
data = data.(variable_in_question);
outlier = isoutlier(data, 'quartiles');
 
%indicate rows with outliers plus their amount
indices_outlier = find(outlier);
number_outlier = height(indices_outlier);

