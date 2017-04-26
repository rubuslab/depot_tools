DEPS = [
  "recipe_engine/json",
  "recipe_engine/properties",
  "recipe_engine/step",
]


def RunSteps(api):
  api.step("dump properties", ["echo", api.json.dumps(api.properties.thaw())])


def GenTests(api):
  yield api.test("basic") + api.properties(hello="world", yes=1)
