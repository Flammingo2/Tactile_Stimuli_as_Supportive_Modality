{
    "block_id": "mix_learning_demo",
    "block_title": "mix_learning_demo_block_title",
    "intro_gui": ["connect_test_start_command", "back_to_menu_command", "block_title", "mix_learning_demo_block_description"],
    "summary_gui": ["mix_learning_demo_block_summary", "next_command", "back_to_menu_command"],
    "save_results": false,
    "trials": {},
    "pages": [
        {
            "after_trials": [0],
            "page_timeout": 4,
            "page_gui": ["countdown_fixation_cross"]
        }
    ],
    "trials_builder": {
    "total_trials": 4,
        "default_trial_config": {
            "duration": 6,
            "stimulus_start_time": [0.5, 1.5, 0.01],
            "stimulus_duration": 4,
            "trial_gui": "fixation_cross",
            "visual_stimulus_gui": "colored_color_label"
        },
        "trial_schema": [
            {
                "weight": 1,
                "vibration_stimulus": "BLUE",
                "visual_stimulus_color": "BLUE",
                "visual_stimulus_text": "PEKU"
            },
            {
                "weight": 1,
                "vibration_stimulus": "GREEN",
                "visual_stimulus_color": "GREEN",
                "visual_stimulus_text": "IDET"
            },
            {
                "weight": 1,
                "visual_stimulus_color": "RED",
                "visual_stimulus_text": "TIDA"
            },
            {
                "weight": 1,
                "visual_stimulus_color": "YELLOW",
                "visual_stimulus_text": "LOHI"
            }
            
        ]
    }
},