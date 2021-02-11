% If bot code review label vote value is 1, bypass default submit rules
submit_rule(Out) :-
  gerrit:default_submit(In),
  In =.. [submit | A],
  check_bot_commit(A, B),
  Out =.. [submit | B].
  
% If ‘Bot-Commit’ +1 vote exists,
% removes the ‘Code-Review’ and ‘Verified’ Labels
% If no vote is found, the predicate removes the
% ‘Bot-Commit’ label
% The ‘Bot-Commit’ label is for use by verifiably built bots
% to skip Code-Review
check_bot_commit(Ls, R) :-
  (gerrit:commit_label(label('Bot-Commit', 1), _)
  -> gerrit:remove_label(Ls, label('Code-Review', _), R)
; gerrit:remove_label(Ls, label('Bot-Commit', _), R)
).