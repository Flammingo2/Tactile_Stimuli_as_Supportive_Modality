% Create list of all subject numbers
list_subjects = 1:16;

%% DATA IMPORT
% Import all data in from file named 'summary_all_subjects'
data = spreadsheetDatastore('summary_all_subjects.xlsx');

data.SelectedVariableNames = {'VP_Nr', 'position', 'day',...
                    'visual_stimulus_text','visual_stimulus_color',...
                    'congruency', 'correct_answer', 'answer', 'accuracy',...
                    'vibration', 'stimulus_start_time', 'voice_onset',...
                    'reaction_time'};
data.VariableTypes = {'double','double', 'double', 'char', 'char',...
                    'char', 'char', 'char', 'double', 'double', 'double',...
                    'double', 'double'};

data = read(data);

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

%% Remove trials with RTs below 250ms
% Find rows with RT lower than 0.25
toDelete = data.reaction_time < 0.25;

% Calculate frequency of artefact answers
artefact_answer_frequency = tabulate(toDelete);
artefact_answer_frequency = 100 - artefact_answer_frequency{1,3}

% Delete rows of artefact answers
toDelete = find(toDelete);
data(toDelete,:) = [];

% FINAL For plotting accuracy
writetable(data, 'replication_MyAnalysis_our_data_to_plot_accuracy.csv');
data_plot_accuracy = data;

%% Descriptive Statistik
% Calculate means of accuracy and RT per treatment and VP
[means, grps] = grpstats([data.accuracy data.reaction_time],...
                {data.VP_Nr,data.day,data.congruency,data.vibration},...
                {'mean', 'gname'});
% Create table with means and factor variables
grps1 = str2double(grps(:,1:3));
grps2 = string(grps(:,4));
means_data = table(grps1(:,1), grps1(:,2), grps(:,3), grps2, means(:,1),...
                'VariableNames',...
                {'VP_Nr' 'day' 'congruency' 'vibration' 'accuracy_mean'} );

%% DELETE FALSE ANSWER TRIALS
% Find false answer trials
toDelete = data.accuracy == 0;

% Calculate frequency of false answers
false_answer_frequency = tabulate(toDelete);
false_answer_frequency = 100 - false_answer_frequency{1,3}

% Delete rows of false answers
toDelete = find(toDelete);
data(toDelete,:) = [];

%% Outlier detection with Winzorising
% IQR outlier detection with Winsorisizing
data_cleaned = [];
number_outlier_all = 0;

% Detect outliers individually per subjects
for subjects = 1:16  
    % Detect outliers per measurement day
    for day = 1:2
        % Detect outliers per modality
        for modality = 0:1       
            % Detect outliers per congruency
            options = ["congruent","incongruent"];
            for counter = 1:2
                congruency = options(counter);         
                % Determine subset of data
                treatment = data(data.VP_Nr == subjects & ...
                            data.day == day & ...
                            data.vibration == modality &  ...
                            strcmpi(data.congruency, congruency), :); 
                % Find outlier indices using self-written function
                % 'winsor'
                [treatment, number_outlier] = winsor(treatment, [25,75]);

                % Create new Table with cleaned data
                data_cleaned = [data_cleaned; treatment];
                
                % Calculate number of outliers and add up
                number_outlier_all = number_outlier_all + number_outlier;
            end
            

        end


    end
    

end
% Print out number of outliers
number_outlier_all
% Calculate frequency of outliers and print out
outlier_frequency_all = (number_outlier_all/(800*16)*100)

data = data_cleaned;

% FINAL For plotting RT
writetable(data, 'replication_MyAnalysis_all_data_to_plot_RT.csv');
data_plot_RT = data;

%% Log-Transformation on accuracy
% Transformation to get closer to the normal distribution as a
% precondition to do repeated measures ANOVAs
data_accuracy_log = array2table(reallog(means_data.accuracy_mean),...
                        'VariableNames', {'log_accuracy_mean'});
% Add log-data as new column to means_data
means_data_log = [means_data data_accuracy_log];





%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%




%% ACCURACY repeated measure N-way ANOVA within subject design
%% Create data for ranova for accuracy
% Create table with one column per condition storing the responses(accuracy)
data_accuracy = [];

% Looping through every subject
for pointer = 1:16  
    subject = list_subjects(pointer);
    % Selecting only rows of one subject
    vp = means_data_log(means_data_log.VP_Nr == subject, :);
    % Store the eight conditions horizontally and concatenate all of them vertically
    data_accuracy = [data_accuracy;[vp.log_accuracy_mean']];
end

% Convert to a table
data_accuracy = array2table(data_accuracy, 'VariableNames',...
                {'day1_congruent_tactile0','day1_congruent_tactile1',...
                'day1_incongruent_tactile0','day1_incongruent_tactile1',...
                'day2_congruent_tactile0','day2_congruent_tactile1',...
                'day2_incongruent_tactile0','day2_incongruent_tactile1'});

%% Prepare for fitrm()accuracy
% Create a table reflecting the within subject factors 'day', 'congruency',
% and 'vibration' and their levels
factorNames = {'day','congruency','vibration'};
within = table({'1';'1';'1';'1';'2';'2';'2';'2'},...
                {'congruent';'congruent';'incongruent';'incongruent';...
                'congruent';'congruent';'incongruent';'incongruent'},...
                {'T';'V';'T';'V';'T';'V';'T';'V'},...
                'VariableNames',factorNames);

% Fit the repeated measures model
rm = fitrm(data_accuracy,'day1_congruent_tactile0,day1_congruent_tactile1, day1_incongruent_tactile0,day1_incongruent_tactile1,day2_congruent_tactile0,day2_congruent_tactile1,day2_incongruent_tactile0,day2_incongruent_tactile1~1','WithinDesign',within);

%% RANOVA accuracy
% Run my repeated measures anova here
[ranovatbl, A, C, D] = ranova(rm, 'WithinModel','day*congruency*vibration');
% Print out the results
ranovatbl

% Store results in ranova_accuracy
ranova_accuracy.ranovatbl = ranovatbl;
ranova_accuracy.A = A;
ranova_accuracy.C = C;
ranova_accuracy.D = D;

%% Accuracy Testing for Normal-Distribution in all combinations
% Do the lilliefors test for all treatments
% Loop through all treatments
for column = 1:8
    % Apply the Lilliefors Test to all treatments
    [h,p,k,c] = lillietest(table2array(data_accuracy(:,column)));
    % Print out corresponding statement
    if h == 0
        strcat("Accuracy data NOT normal distributed in condition ",...
                                        num2str(column))
    else 
        strcat("Accuracy data normal distributed in ", num2str(column))
    end
end






%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%









%% RT repeated measure N-way ANOVA with within subject design 
%% Create data for ranova for RT
% Create table with one column per condition storing the responses(reaction_time)
column = 1;
% Looping again through all treatments within every subject
for pointer = 1:16  
    subject = list_subjects(pointer);
    % per measurement day
    for day = 1:2
        % per modality
        for pointer2 = 1:2
            options = ["congruent","incongruent"];
            congruency = options(pointer2);
            % per modality
            for modality = 0:1
                % Restart column counter if necessary
                if column == 9
                    column = 1;
                end
                % Determine subset of data presenting one treatment within
                % one subject
                condition = data(data.VP_Nr == subject & ...
                                 data.day == day & ...
                                 strcmpi(data.congruency, congruency) &  ...
                                 data.vibration == modality, :);
                             
                % For conditions with less than 154 values 
                % (missing data, outlier etc) 
                % (maximum number of trials in one treatment is apparently 
                % 154, even though in perfect conditions it should have 
                % been 100), fill trials up with NaNs(to be able to form 
                % a table with values of the same VP in a row)
                while height(condition) < 154
                    condition = [condition; array2table(NaN(1,13),...
                        'VariableNames',condition.Properties.VariableNames)];                   
                end
                % Store data of one treatment of one subject, 
                % repeat for all others
                % Store under spcified name
                conditions_RT.(strcat('subject_',num2str(subject), '_',...
                        num2str(column))) = condition.reaction_time;
                column = column + 1;
            end
        end
    end
    % Merge data of each subjects vertically, build a table
    vp_RT.(strcat('subject_', num2str(subject))) = table(...
               conditions_RT.(strcat('subject_', num2str(subject), '_1')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_2')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_3')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_4')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_5')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_6')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_7')),...
               conditions_RT.(strcat('subject_', num2str(subject), '_8')));
end

% Merge subject tables horizontally
data_RT = [vp_RT.subject_1; vp_RT.subject_2; vp_RT.subject_3;...
           vp_RT.subject_4; vp_RT.subject_5; vp_RT.subject_6;...
           vp_RT.subject_7; vp_RT.subject_8; vp_RT.subject_9;...
           vp_RT.subject_10; vp_RT.subject_11; vp_RT.subject_12;...
           vp_RT.subject_13; vp_RT.subject_14; vp_RT.subject_15;...
           vp_RT.subject_16];

% Give names to columns of the table
data_RT.Properties.VariableNames = {'day1_congruent_tactile0',...
                'day1_congruent_tactile1', 'day1_incongruent_tactile0',...
                'day1_incongruent_tactile1','day2_congruent_tactile0',...
                'day2_congruent_tactile1','day2_incongruent_tactile0',...
                'day2_incongruent_tactile1'};

%% Prepare for fitrm()RT
% Create a table reflecting the within subject factors 'day', 'congruency', 
% and 'vibration' and their levels
factorNames = {'day','congruency','vibration'};
within = table({'1';'1';'1';'1';'2';'2';'2';'2'},...
                {'congruent';'congruent';'incongruent';'incongruent';...
                'congruent';'congruent';'incongruent';'incongruent'},...
                {'T';'V';'T';'V';'T';'V';'T';'V'},...
                'VariableNames',factorNames);

% Fit the repeated measures model
rm = fitrm(data_RT,'day1_congruent_tactile0,day1_congruent_tactile1, day1_incongruent_tactile0,day1_incongruent_tactile1,day2_congruent_tactile0,day2_congruent_tactile1,day2_incongruent_tactile0,day2_incongruent_tactile1~1','WithinDesign',within);

%% RANOVA RT
% Run the repeated measures anova here
[ranovatbl, A, C, D] = ranova(rm, 'WithinModel','day*congruency*vibration');
% Print the results
ranovatbl

% Store results in ranova_RT
ranova_RT.ranovatbl = ranovatbl;
ranova_RT.A = A;
ranova_RT.C = C;
ranova_RT.D = D;

%% Reaction_Time: Testing for Normal-Distribution in all combinations
% Do lilliefors test on each treatment of reaction_time
% Loop again through every treatment per each subject
for column = 1:8
    [h,p,k,c] = lillietest(table2array(data_RT(:,column)));
    
    % Print out corresponding statement
    if h == 0
        strcat("Reaction_time data NOT normal distributed in condition ",...
                                            num2str(column))
    else 
        strcat("Reaction_time data normal distributed in ", num2str(column))
    end
end

%% Grouping Test 
% each VP on distribution of tactile vs visual

subjects = list_subjects;
for counter = 1:16
    subject = subjects(counter);
    
    %test grouping on each VP over tactile/visual
    group_tactile = means_data(means_data.VP_Nr == subject & means_data.vibration == '1',:);
    group_visual = means_data(means_data.VP_Nr == subject & means_data.vibration == '0',:);
 
    h = kstest2(group_tactile.accuracy_mean,group_visual.accuracy_mean);
    grouping_test.(strcat("subject_",num2str(subject))) = h;

    
    %test grouping on each VP & congruency over tactile/visual
    %congruency = congruent
    group_tactile_congruent = means_data(means_data.VP_Nr == subject & means_data.vibration == '1' & strcmpi(means_data.congruency,'congruent'),:);
    group_visual_congruent = means_data(means_data.VP_Nr == subject & means_data.vibration == '0' & strcmpi(means_data.congruency,'congruent'),:);
    
    h = kstest2(group_tactile_congruent.accuracy_mean,group_visual_congruent.accuracy_mean);
    grouping_test_congruent.(strcat("subject_",num2str(subject))) = h;
    
    %congruency = incongruent
    group_tactile_incongruent = means_data(means_data.vibration == '1' & strcmpi(means_data.congruency,'incongruent'),:);
    group_visual_incongruent = means_data(means_data.vibration == '0' & strcmpi(means_data.congruency,'incongruent'),:);
    
    h = kstest2(group_tactile_incongruent.accuracy_mean,group_visual_incongruent.accuracy_mean);
    grouping_test_incongruent.(strcat("subject_",num2str(subject))) = h;

    %test grouping on each VP & day over tactile/visual
    %day = 1
    group_tactile_1 = means_data(means_data.VP_Nr == subject & means_data.vibration == '1' & means_data.day == 1,:);
    group_visual_1 = means_data(means_data.VP_Nr == subject & means_data.vibration == '0' & means_data.day == 1,:);
    
    h = kstest2(group_tactile_1.accuracy_mean,group_visual_1.accuracy_mean);
    grouping_test_day_1.(strcat("subject_",num2str(subject))) = h;
    
    %day = 2
    group_tactile_2 = means_data(means_data.vibration == '1' & means_data.day == 2,:);
    group_visual_2 = means_data(means_data.vibration == '0' & means_data.day == 2,:);
    
    h = kstest2(group_tactile_2.accuracy_mean,group_visual_2.accuracy_mean);
    grouping_test_day_2.(strcat("subject_",num2str(subject))) = h;

end

grouping_test
grouping_test_congruent
grouping_test_incongruent
grouping_test_day_1
grouping_test_day_2


%% Save variables/data to .mat file to load into python
save 'replication_RANOVA_MyAnalysis_our_accuracy_data_to_plot.mat' data_plot_accuracy means_data answer_frequencies missing_data_frequency ranova_accuracy grouping_test grouping_test_congruent grouping_test_incongruent;
save 'replication_RANOVA_MyAnalysis_our_RT_data_to_plot.mat' data_plot_RT ranova_RT;