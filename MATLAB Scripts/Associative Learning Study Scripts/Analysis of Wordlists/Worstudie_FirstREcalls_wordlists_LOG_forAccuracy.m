%% DATA IMPORT
% Import all data in from file named 'vp_dataset' to a table
data = spreadsheetDatastore('vp_dataset.xlsx');
data.SelectedVariableNames = {'VP_Nr', 'position', 'day', 'recall', 'visual_stimulus_text', 'word_list', 'number_recall', 'tactile', 'correct_answer', 'answer', 'accuracy', 'reaction_time'};
data.VariableTypes = {'double','double', 'double', 'double', 'char', 'double', 'double' 'char', 'char', 'char', 'double', 'double'};
data = read(data);

%% Delete VP18
% Find rows of subject number 18
toDelete = data.VP_Nr == 18;

% Delete rows of subject number 18
toDelete = find(toDelete);
data(toDelete,:) = [];

%% Remove trials with RTs below 150ms
% Find rows with reaction time lower than 150ms
toDelete = data.reaction_time < 0.15;

% Calculate frequency of artefact answers
artefact_answer_frequency = tabulate(toDelete);
artefact_answer_frequency = 100 - artefact_answer_frequency{1,3}

% Delete rows of artefact answers
toDelete = find(toDelete);
data(toDelete,:) = [];

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

%% ACCURACY repeated measure N-way ANOVA within subject design
% Within-subject factors: day x WORDLISTS x modality
wordlist_data = data;

%% Create data for ranova for accuracy
%% Delete number_recall == 2 words
% Find rows of number_recall == 2
toDelete = wordlist_data.number_recall == 2;

% Delete rows of second recalls
toDelete = find(toDelete);
wordlist_data(toDelete,:) = [];

% FINAL For plotting accuracy
writetable(wordlist_data, 'wortstudie_FirstRecalls_wordlists_to_plot_accuracy.csv');

%% Calculate means of accuracy and RT per treatment and subjects
[means, grps] = grpstats([wordlist_data.accuracy wordlist_data.reaction_time], {wordlist_data.VP_Nr, wordlist_data.day, wordlist_data.word_list}, {'mean', 'gname'});

% Create table with means and factor variables
grps1 = str2double(grps(:,1:3));
wordlist_means_data = table(grps1(:,1), grps1(:,2), grps(:,3), means(:,1), 'VariableNames', {'VP_Nr' 'day' 'wordlist' 'accuracy_mean'} );

%% Log-Transformation on Accuracy
% Transformation to get closer to the normal distribution wich is a
% precondition to use the rANOVA

% Create column 
wordlist_data_accuracy_log = array2table(reallog(wordlist_means_data.accuracy_mean), 'VariableNames', {'log_accuracy_mean'});
% Append log column 
wordlist_means_data_log = [wordlist_means_data wordlist_data_accuracy_log]

%% DELETE FALSE ANSWER TRIALS (for RT Data creation)
% Find false answer trials
toDelete = wordlist_data.accuracy == 0;

% Delete rows of false answers
toDelete = find(toDelete);
wordlist_data(toDelete,:) = [];

% FINAL For plotting RT
writetable(wordlist_data, 'wortstudie_FirstRecalls_wordlists_to_plot_RT.csv');

%% Create table with one column per condition storing the responses
% (accuracy)
%Create table with one column per condition storing the responses(accuracy)
wordlist_data_accuracy = [];
% Create list of all subject numbers
subjects = [2, 6, 7, 8, 9, 10,11, 12, 13, 14, 15, 16, 17, 19];
% Loop through all subjects
for pointer = 1:14  
    subject = subjects(pointer);
    % Get all rows of one subject
    vp = wordlist_means_data_log(wordlist_means_data_log.VP_Nr == subject, :);
    %Store the eight conditions horizontally and concatenate all of them vertically
    wordlist_data_accuracy = [wordlist_data_accuracy;[vp.accuracy_mean']];
    
end
% Convert to a table
wordlist_data_accuracy = array2table(wordlist_data_accuracy, 'VariableNames', {'day1_wordlist1','day1_wordlist2', 'day1_wordlist3','day1_wordlist4','day2_wordlist1','day2_wordlist2','day2_wordlist3','day2_wordlist4'});

%% Prepare for fitrm()accuracy
% Create a table reflecting the within subject factors 'day', 'number_recall', and 'tactile' and their levels
factorNames = {'day','wordlist'};
within = table({'1';'1';'1';'1';'2';'2';'2';'2'},{'wordlist_1';'wordlist_2';'wordlist_3';'wordlist_4';'wordlist_1';'wordlist_2';'wordlist_3';'wordlist_4'},'VariableNames',factorNames);

% Fit the repeated measures model
rm = fitrm(wordlist_data_accuracy,'day1_wordlist1, day1_wordlist2, day1_wordlist3, day1_wordlist4, day2_wordlist1, day2_wordlist2, day2_wordlist3, day2_wordlist4~1','WithinDesign',within);

%% RANOVA accuracy
% Run the repeated measures anova
[ranovatbl, A, C, D] = ranova(rm, 'WithinModel','day*wordlist');
% Print the results
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
    [h,p,k,c] = lillietest(table2array(wordlist_data_accuracy(:,column)));
    % Print out corresponding statement
    if h == 0
        strcat("Accuracy data NOT normal distributed in condition ", num2str(column))
    else 
        strcat("Accuracy data normal distributed in ", num2str(column))
    end
end
