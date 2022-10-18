[1mdiff --git a/presubmit_canned_checks.py b/presubmit_canned_checks.py[m
[1mindex 0638fb2d..4837183d 100644[m
[1m--- a/presubmit_canned_checks.py[m
[1m+++ b/presubmit_canned_checks.py[m
[36m@@ -108,6 +108,17 @@[m [mdef CheckDoNotSubmitInDescription(input_api, output_api):[m
   return [][m
 [m
 [m
[32m+[m[32mdef CheckCorpLinksInDescription(input_api, output_api):[m
[32m+[m[32m  """Checks that the description doesn't contain corp links."""[m
[32m+[m[32m  if 'corp.google' in input_api.change.DescriptionText():[m
[32m+[m[32m    return [[m
[32m+[m[32m        output_api.PresubmitError([m
[32m+[m[32m            'Corp link is present in the changelist description.')[m
[32m+[m[32m    ][m
[32m+[m
[32m+[m[32m  return [][m
[32m+[m
[32m+[m
 def CheckChangeHasDescription(input_api, output_api):[m
   """Checks the CL description is not empty."""[m
   text = input_api.change.DescriptionText()[m
[36m@@ -214,6 +225,16 @@[m [mdef CheckDoNotSubmitInFiles(input_api, output_api):[m
   return [][m
 [m
 [m
[32m+[m[32mdef CheckCorpLinksInFiles(input_api, output_api, source_file_filter=None):[m
[32m+[m[32m  """Checks that files do not contain a corp link."""[m
[32m+[m[32m  errors = _FindNewViolationsOfRule(lambda _, line: 'corp.google' not in line,[m
[32m+[m[32m                                    input_api, source_file_filter)[m
[32m+[m[32m  text = '\n'.join('Found corp link in %s' % loc for loc in errors)[m
[32m+[m[32m  if text:[m
[32m+[m[32m    return [output_api.PresubmitError(text)][m
[32m+[m[32m  return [][m
[32m+[m
[32m+[m
 def GetCppLintFilters(lint_filters=None):[m
   filters = OFF_UNLESS_MANUALLY_ENABLED_LINT_FILTERS[:][m
   if lint_filters is None:[m
[36m@@ -712,35 +733,6 @@[m [mdef CheckLicense(input_api, output_api, license_re=None, project_name=None,[m
   return [][m
 [m
 [m
[31m-def CheckCorpLinks(input_api, output_api, source_file_filter=None):[m
[31m-  """Checks that no corp links are present in any files or in the description.[m
[31m-  """[m
[31m-  corp_re = input_api.re.compile(r'corp\.google')[m
[31m-[m
[31m-  desc_errors = [][m
[31m-  text = input_api.change.DescriptionText()[m
[31m-  if corp_re.search(text):[m
[31m-    desc_errors.append([m
[31m-        output_api.PresubmitPromptWarning('Description contains corp link.'))[m
[31m-[m
[31m-  if input_api.no_diffs:[m
[31m-    return desc_errors[m
[31m-[m
[31m-  file_errors = [][m
[31m-  for f in input_api.AffectedFiles(include_deletes=False,[m
[31m-                                   file_filter=source_file_filter):[m
[31m-    for line_num, line in f.ChangedContents():[m
[31m-      if corp_re.search(line):[m
[31m-        file_errors.append('%s (%d): %s' % (f.LocalPath(), line_num, line))[m
[31m-  if file_errors:[m
[31m-    return [[m
[31m-        output_api.PresubmitPromptWarning('Found corp link in:',[m
[31m-                                          long_text='\n'.join(file_errors))[m
[31m-    ] + desc_errors[m
[31m-[m
[31m-  return desc_errors[m
[31m-[m
[31m-[m
 ### Other checks[m
 [m
 def CheckDoNotSubmit(input_api, output_api):[m
[36m@@ -1476,11 +1468,6 @@[m [mdef PanProjectChecks(input_api, output_api,[m
   results.extend(input_api.canned_checks.CheckLicense([m
       input_api, output_api, license_header, project_name,[m
       source_file_filter=sources))[m
[31m-  snapshot("checking corp links")[m
[31m-  results.extend([m
[31m-      input_api.canned_checks.CheckCorpLinks(input_api,[m
[31m-                                             output_api,[m
[31m-                                             source_file_filter=sources))[m
 [m
   if input_api.is_committing:[m
     if global_checks:[m
[36m@@ -1496,6 +1483,9 @@[m [mdef PanProjectChecks(input_api, output_api,[m
           input_api, output_api))[m
       results.extend(input_api.canned_checks.CheckDoNotSubmitInDescription([m
           input_api, output_api))[m
[32m+[m[32m      results.extend([m
[32m+[m[32m          input_api.canned_checks.CheckCorpLinksInDescription([m
[32m+[m[32m              input_api, output_api))[m
       if input_api.change.scm == 'git':[m
         snapshot("checking for commit objects in tree")[m
         results.extend(input_api.canned_checks.CheckForCommitObjects([m
[36m@@ -1503,6 +1493,10 @@[m [mdef PanProjectChecks(input_api, output_api,[m
     snapshot("checking do not submit in files")[m
     results.extend(input_api.canned_checks.CheckDoNotSubmitInFiles([m
         input_api, output_api))[m
[32m+[m[32m    snapshot("checking corp links in files")[m
[32m+[m[32m    results.extend([m
[32m+[m[32m        input_api.canned_checks.CheckCorpLinksInFiles([m
[32m+[m[32m            input_api, output_api, source_file_filter=sources))[m
   snapshot("done")[m
   return results[m
 [m
[1mdiff --git a/tests/presubmit_unittest.py b/tests/presubmit_unittest.py[m
[1mindex acda2946..5cbb1d99 100755[m
[1m--- a/tests/presubmit_unittest.py[m
[1m+++ b/tests/presubmit_unittest.py[m
[36m@@ -1953,6 +1953,18 @@[m [mclass CannedChecksUnittest(PresubmitTestsBase):[m
         'DO NOTSUBMIT', None, 'DO NOT ' + 'SUBMIT', None,[m
         presubmit.OutputApi.PresubmitError)[m
 [m
[32m+[m[32m  def testCannedCheckCorpLinksInDescription(self):[m
[32m+[m[32m    self.DescriptionTest(presubmit_canned_checks.CheckCorpLinksInDescription,[m
[32m+[m[32m                         'chromium.googlesource.com',[m
[32m+[m[32m                         'chromium.git.corp.google.com',[m
[32m+[m[32m                         presubmit.OutputApi.PresubmitPromptWarning, False)[m
[32m+[m
[32m+[m[32m  def testCannedCheckCorpLinksInFiles(self):[m
[32m+[m[32m    self.ContentTest(presubmit_canned_checks.CheckCorpLinks,[m
[32m+[m[32m                     'chromium.googlesource.com', None,[m
[32m+[m[32m                     'chromium.git.corp.google.com', None,[m
[32m+[m[32m                     presubmit.OutputApi.PresubmitPromptWarning)[m
[32m+[m
   def testCheckChangeHasNoStrayWhitespace(self):[m
     self.ContentTest([m
         lambda x,y,z:[m
[36m@@ -2326,8 +2338,8 @@[m [mthe current line as well![m
 [m
   def testCheckCorpLinks(self):[m
     self.ContentTest(presubmit_canned_checks.CheckCorpLinks,[m
[31m-                     "chromium.googlesource.com", None,[m
[31m-                     "chromium.git.corp.google.com", None,[m
[32m+[m[32m                     'chromium.googlesource.com', None,[m
[32m+[m[32m                     'chromium.git.corp.google.com', None,[m
                      presubmit.OutputApi.PresubmitPromptWarning)[m
 [m
   def testCannedCheckTreeIsOpenOpen(self):[m
