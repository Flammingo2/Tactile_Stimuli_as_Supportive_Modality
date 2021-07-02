%% DATA IMPORT
% Import all data in from file named 'vp_dataset' to a table
data = spreadsheetDatastore('vp_dataset.xlsx');
data.SelectedVariableNames = {'VP_Nr', 'position', 'day', 'recall', 'visual_stimulus_text', 'word_list', 'number_recall', 'tactile', 'correct_answer', 'answer', 'accuracy', 'reaction_time'};
data.VariableTypes = {'double','double', 'double', 'double', 'char', 'double', 'double' 'char', 'char', 'char', 'double', 'double'};
data = read(data);

%% Delete VP18
% Because of disruption during the experiments
% Find rows of VP18
toDelete = data.VP_Nr == 18;

% Delete rows of false answers
toDelete = find(toDelete);
data(toDelete,:) = [];

rohdaten = data;

%% MISSING DATA
% Delete all rows with missing data including row with 'NONE'
answer_frequencies = tabulate(data.answer)
data = standardizeMissing(data,'NONE');
[data, missing_data] = rmmissing(data);

% Calculate frequency of missing data
missing_data_frequency = tabulate(missing_data);
row_number = size(missing_data_frequency);
if row_number(1) > 1
    number_missing_data = missing_data_frequency{2,2};
else
    number_missing_data = 0;
end
missing_data_frequency = 100 - missing_data_frequency{1,3}   

%% Remove artefacts: trials with RTs below 150ms
% Find indices of trials to delete
toDelete = data.reaction_time < 0.15;

% Calculate frequency of artefact answers
artefact_answer_frequency = tabulate(toDelete);
artefact_answer_frequency = 100 - artefact_answer_frequency{1,3}

% Delete rows of artefact answers
toDelete = find(toDelete);
data(toDelete,:) = [];

% FINAL For plotting accuracy
writetable(data, 'wortstudie_to_plot_accuracy.csv');
data_plot_accuracy = data;

%% Descriptive Statistics
% Get mean accuracies and reaction times
% regarding levels of the factor day
[means, grps] = grpstats([data.accuracy data.reaction_time], {data.day}, {'mean', 'gname'});
% regarding levels of the factor day and modality
[means, grps] = grpstats([data.accuracy data.reaction_time], {data.day, data.tactile}, ...
    {'mean', 'gname'});
% regarding levels of the factor day, number of recall and modality
[means, grps] = grpstats([data.accuracy data.reaction_time], ...
                    {data.day, data.number_recall, data.tactile}, ...
                    {'mean', 'gname'});

%% Calculate means of accuracy and RT per treatment and VP
[means, grps] = grpstats([data.accuracy data.reaction_time], ...
                {data.VP_Nr, data.day, data.number_recall, data.tactile}, ...
                {'mean', 'gname'});

% Create table with means and factor variables
grps1 = str2double(grps(:,1:3));
grps2 = string(grps(:,4));
means_data = table(grps1(:,1), grps1(:,2), grps(:,3), grps2, means(:,1), ...
                'VariableNames', {'VP_Nr' 'day' 'number_recall' 'tactile' 'accuracy_mean'} );

%% DELETE FALSE ANSWER TRIALS
% Find false answer trials
toDelete = data.accuracy == 0;

% Calculate frequency of false answers
false_answer_frequency = tabulate(toDelete);
false_answer_frequency = 100 - false_answer_frequency{1,3}

% Delete rows of false answers
toDelete = find(toDelete);
data(toDelete,:) = [];

% FINAL For plotting RT
writetable(data, 'wortstudie_to_plot_RT.csv');
data_plot_RT = data;

%% Log Transformation on Accuracy and Reaction Time
% Reaction Time LOG-transformation
data_RT_log = array2table(log(data.reaction_time), ...
                    'VariableNames', {'log_reaction_time'});
data = [data data_RT_log];

% Accuracy LOG-transformation
data_accuracy_log = array2table(log(means_data.accuracy_mean), ...
                    'VariableNames', {'log_accuracy_mean'});
means_data_log = [means_data data_accuracy_log];

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%




%% ACCURACY repeated measure N-way ANOVA within subject design
%% Create data for ranova for accuracy
% Create table with one column per condition storing the responses(accuracy)
data_accuracy = [];
% Create list of all subject numbers
subjects = [2, 6, 7, 8, 9, 10,11, 12, 13, 14, 15, 16, 17, 19];
% Loop through all subjects
for pointer = 1:14  
    subject = subjects(pointer);
    % Get all rows of one subject
    vp = means_data_log(means_data_log.VP_Nr == subject, :);
    % Store the eight conditions horizontally and concatenate all of them vertically
    data_accuracy = [data_accuracy;[vp.log_accuracy_mean']];
    
end

% Convert to a table
data_accuracy = array2table(data_accuracy, 'VariableNames', ...
                {'day1_recall1_tactile0','day1_recall1_tactile1', 'day1_recall2_tactile0',...
                'day1_recall2_tactile1','day2_recall1_tactile0','day2_recall1_tactile1',...
                'day2_recall2_tactile0','day2_recall2_tactile1'});

%% Prepare for fitrm()accuracy
% Create a table reflecting the within subject factors 'day', 'number_recall', and 'tactile' and their levels
factorNames = {'day','number_recall','tactile'};
within = table({'1';'1';'1';'1';'2';'2';'2';'2'},...
                {'recall_1';'recall_1';'recall_2';'recall_2';'recall_1';'recall_1';...
                'recall_2';'recall_2'},{'T';'V';'T';'V';'T';'V';'T';'V'},...
                'VariableNames',factorNames);

% Fit the repeated measures model
rm = fitrm(data_accuracy,...
            'day1_recall1_tactile0,day1_recall1_tactile1, day1_recall2_tactile0,day1_recall2_tactile1,day2_recall1_tactile0,day2_recall1_tactile1,day2_recall2_tactile0,day2_recall2_tactile1~1','WithinDesign',...
            within);

%% RANOVA accuracy
% Run the repeated measures anova
[ranovatbl, A, C, D] = ranova(rm, 'WithinModel','day*number_recall*tactile');
% Print out the results
ranovatbl
% Store results in ranova_accuracy
ranova_accuracy.ranovatbl = ranovatbl;
ranova_accuracy.A = A;
ranova_accuracy.C = C;
ranova_accuracy.D = D;

%% Accuracy Testing for Normal-Distribution in all combinations
% Do the Lilliefors test for all treatments
% Loop through all treatments
for column = 1:8
    % Apply the Lilliefors Test to all treatments
    
%     % Save figures for estimation of normality
%     histogram(table2array(data_accuracy(:,column)))
%     this_name = strcat("Accuracy_condition_",num2str(column));
%     saveas(gcf, this_name, 'png');
    
    [h,p,k,c] = lillietest(table2array(data_accuracy(:,column)));
    % Print out corresponding statement
    if h == 1
        strcat("Accuracy data NOT normal distributed in condition ", num2str(column))
    else 
        strcat("Accuracy data normal distributed in ", num2str(column))
    end
end






%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%









%% RT repeated measure N-way ANOVA within subject design 
%% Create data for ranova for RT
%C reate table with one column per condition storing the responses(reaction_time)
column = 1;
% Create list of all subject numbers
subjects = [2, 6, 7, 8, 9, 10,11, 12, 13, 14, 15, 16, 17, 19];
for pointer = 1:14  
    subject = subjects(pointer);
    % per measurement day
    for day = 1:2
        % per modality
        for number_recall = 1:2
            
            % per modality
            vibration = ["false","true"];
            for counter = 1:2
                modality = vibration(counter);  
                % Reset column pointer if necessary
                if column == 9
                    column = 1;
                end
                condition = data(data.VP_Nr == subject & data.day == day & data.number_recall == number_recall &  strcmpi(data.tactile, modality), :);
                % For conditions with less than 100 values (missing data, outlier etc), fill
                % trials up with NaNs (to be able to form a table with
                % values of the same VP in a row
                while height(condition) < 40
                    condition = [condition; array2table(NaN(1,13),'VariableNames',condition.Properties.VariableNames)];                   
                end
                % Get data of all treatment for all VP each
                conditions_RT.(strcat('subject_',num2str(subject), '_', num2str(column))) = condition.log_reaction_time;

                column = column + 1;
            end
        end
    end
    % Merge data of each subjects vertically, build a table
    vp_RT.(strcat('subject_', num2str(subject))) = table(...
                                conditions_RT.(strcat('subject_', num2str(subject), '_1')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_2')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_3')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_4')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_5')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_6')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_7')), ...
                                conditions_RT.(strcat('subject_', num2str(subject), '_8')));
end

% Merge subject tables  horizontally
data_RT = [vp_RT.subject_2; ...
            vp_RT.subject_6; ...
            vp_RT.subject_7; ...
            vp_RT.subject_8; ...
            vp_RT.subject_9; ...
            vp_RT.subject_10; ...
            vp_RT.subject_11; ...
            vp_RT.subject_12; ...
            vp_RT.subject_13; ...
            vp_RT.subject_14; ...
            vp_RT.subject_15; ...
            vp_RT.subject_16; ...
            vp_RT.subject_17; ...
            vp_RT.subject_19];

% Give names to columns of the table
data_RT.Properties.VariableNames = {'day1_recall1_tactile0','day1_recall1_tactile1', ...
                                    'day1_recall2_tactile0','day1_recall2_tactile1',...
                                    'day2_recall1_tactile0','day2_recall1_tactile1',...
                                    'day2_recall2_tactile0','day2_recall2_tactile1'};

%% Prepare for fitrm()RT
% Create a table reflecting the within subject factors 'day', 'number_recall', and 'tactile' and their levels
factorNames = {'day','number_recall','tactile'};
within = table({'1';'1';'1';'1';'2';'2';'2';'2'},...
                {'recall_1';'recall_1';'recall_2';'recall_2';'recall_1';'recall_1';...
                'recall_2';'recall_2'},{'T';'V';'T';'V';'T';'V';'T';'V'},...
                'VariableNames',factorNames);

% Fit the repeated measures model
rm = fitrm(data_RT,...
        'day1_recall1_tactile0,day1_recall1_tactile1, day1_recall2_tactile0,day1_recall2_tactile1,day2_recall1_tactile0,day2_recall1_tactile1,day2_recall2_tactile0,day2_recall2_tactile1~1','WithinDesign',...
        within);

%% RANOVA RT
% Run the repeated measures anova
[ranovatbl, A, C, D] = ranova(rm, 'WithinModel','day*number_recall*tactile');
% Print the results
ranovatbl
% Store results in ranova_RT
ranova_RT.ranovatbl = ranovatbl;
ranova_RT.A = A;
ranova_RT.C = C;
ranova_RT.D = D;

%% Reaction_Time: Testing for Normal-Distribution in all combinations
% Do the Lilliefors test on each treatment on the reaction_time
% Loop again through every treatment per each subject
for column = 1:8
    % Test for each treatment of every subject
    [h,p,k,c] = lillietest(table2array(data_RT(:,column)));
    % Print out corresponding statement
    if h == 1
        strcat("Reaction_time data NOT normal distributed in condition ", num2str(column))
    else 
        strcat("Reaction_time data normal distributed in ", num2str(column))
    end
end

%% Grouping Test 
% Within each subject: Testing difference in 
% distribution of tactile vs visual condition

subjects = [2,6,7,8,9,10,11,12,13,14,15,16,17,19];
for counter = 1:14
    subject = subjects(counter);
    
    % Test grouping on each subject over tactile/visual
    group_tactile = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true"),:);
    group_visual = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false"),:);
 
    h = kstest2(group_tactile.accuracy_mean,group_visual.accuracy_mean);
    grouping_test.(strcat("subject_",num2str(subject))) = h;
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Test grouping on each subject & recall_number over tactile/visual
    % number_recall = 1
    group_tactile_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'1'),:);
    group_visual_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'1'),:);
    
    h = kstest2(group_tactile_1.accuracy_mean,group_visual_1.accuracy_mean);
    grouping_test_recall_1.(strcat("subject_",num2str(subject))) = h;
    
    % number_recall = 2
    group_tactile_2 = means_data(strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'2'),:);
    group_visual_2 = means_data(strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'2'),:);
    
    h = kstest2(group_tactile_2.accuracy_mean,group_visual_2.accuracy_mean);
    grouping_test_recall_2.(strcat("subject_",num2str(subject))) = h;
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Test grouping on each subject & day over tactile/visual
    % day = 1
    group_tactile_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & means_data.day == 1,:);
    group_visual_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & means_data.day == 1,:);
    
    h = kstest2(group_tactile_1.accuracy_mean,group_visual_1.accuracy_mean);
    grouping_test_day_1.(strcat("subject_",num2str(subject))) = h;
    
    % day = 2
    group_tactile_2 = means_data(strcmpi(means_data.tactile, "true") & means_data.day == 2,:);
    group_visual_2 = means_data(strcmpi(means_data.tactile, "false") & means_data.day == 2,:);
    
    h = kstest2(group_tactile_2.accuracy_mean,group_visual_2.accuracy_mean);
    grouping_test_day_2.(strcat("subject_",num2str(subject))) = h;
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Test grouping on each subject & all three factors 
    % (day, modality, and number recall)
    % day = 1 
        % number_recall =1
    group_tactile_1_recall_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'1') & means_data.day == 1,:);
    group_visual_1_recall_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'1') & means_data.day == 1,:);
    
    h = kstest2(group_tactile_1_recall_1.accuracy_mean,group_visual_1_recall_1.accuracy_mean);
    grouping_test_day_1_1.(strcat("subject_",num2str(subject))) = h;
    
        % number recall = 2
    group_tactile_1_recall_2 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'2') & means_data.day == 1,:);
    group_visual_1_recall_2 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'2') & means_data.day == 1,:);

    h = kstest2(group_tactile_1_recall_2.accuracy_mean,group_visual_1_recall_2.accuracy_mean);
    grouping_test_day_1_2.(strcat("subject_",num2str(subject))) = h;
    
    % day = 2
        % number recall = 1
    group_tactile_2_recall_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'1') & means_data.day == 2,:);
    group_visual_2_recall_1 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'1') & means_data.day == 2,:);
    
    h = kstest2(group_tactile_2_recall_1.accuracy_mean,group_visual_2_recall_1.accuracy_mean);
    grouping_test_day_2_1.(strcat("subject_",num2str(subject))) = h;
    
        % number recall = 2
    group_tactile_2_recall_2 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "true") & strcmpi(means_data.number_recall,'2') & means_data.day == 2,:);
    group_visual_2_recall_2 = means_data(means_data.VP_Nr == subject & strcmpi(means_data.tactile, "false") & strcmpi(means_data.number_recall,'2') & means_data.day == 2,:);
    
    h = kstest2(group_tactile_2_recall_2.accuracy_mean,group_visual_2_recall_2.accuracy_mean);
    grouping_test_day_2_2.(strcat("subject_",num2str(subject))) = h;

    
end

% Check if some distributions are significantly different 
% (indicated by a 1)
grouping_test
grouping_test_recall_1
grouping_test_recall_2
grouping_test_day_1
grouping_test_day_2
grouping_test_day_1_1
grouping_test_day_1_2
grouping_test_day_2_1
grouping_test_day_2_2

%% Save variables/data to .mat file to load into python
save 'Wortstudie_accuracy_data_to_plot.mat' data_plot_accuracy data means_data_log answer_frequencies missing_data_frequency ranova_accuracy;
save 'Wortstudie_RT_data_to_plot.mat' data_plot_RT data data_RT ranova_RT;