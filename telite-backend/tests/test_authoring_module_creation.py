from types import SimpleNamespace

from app.api.routes import authoring


class DummySession:
    def __init__(self):
        self.flush_calls = 0
        self.commit_calls = 0
        self.refresh_calls = 0
        self.refreshed_instances = []

    def flush(self):
        self.flush_calls += 1

    def commit(self):
        self.commit_calls += 1

    def refresh(self, instance):
        self.refresh_calls += 1
        self.refreshed_instances.append(instance)


def test_persist_and_refresh_reapplies_tenant_context_before_refresh(monkeypatch):
    calls = []

    def fake_apply_tenant_context(db, org_id):
        calls.append((db, org_id))

    monkeypatch.setattr(authoring, "apply_tenant_context", fake_apply_tenant_context)

    db = DummySession()
    instance = SimpleNamespace(org_id=42)

    result = authoring._persist_and_refresh(db, instance, org_id=42)

    assert result is instance
    assert db.flush_calls == 1
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert calls == [(db, 42), (db, 42)]


def test_create_module_persists_quiz_block_with_tenant_aware_helper(monkeypatch):
    class DummyCourseModule:
        sort_order = 0
        course_id = "course-1"
        org_id = 7
        section_id = None
        section = 0
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def to_dict(self):
            return {"id": self.id, "title": self.title, "module_type": self.module_type}

    class DummyLessonBlock:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def to_dict(self):
            return {"id": self.id, "module_id": self.module_id, "block_type": self.block_type}

    class FakeQuery:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

        def count(self):
            return 0

        def scalar(self):
            return self.result

    class FakeDB:
        def __init__(self):
            self.added = []

        def query(self, model):
            if model is authoring.Course:
                return FakeQuery(SimpleNamespace(id="course-1", org_id=7))
            if model is authoring.CourseSection:
                return FakeQuery(None)
            if model is authoring.CourseModule:
                return FakeQuery(None)
            if model is authoring.LessonBlock:
                return FakeQuery(None)
            return FakeQuery(0)

        def add(self, instance):
            self.added.append(instance)

        def commit(self):
            return None
            
        def execute(self, statement, params=None):
            pass

    persist_calls = []

    def fake_persist_and_refresh(db, instance, org_id=None):
        persist_calls.append((instance, org_id))
        if not getattr(instance, "id", None):
            instance.id = 1
        return instance

    monkeypatch.setattr(authoring, "CourseModule", DummyCourseModule)
    monkeypatch.setattr(authoring, "LessonBlock", DummyLessonBlock)
    monkeypatch.setattr(authoring, "_persist_and_refresh", fake_persist_and_refresh)

    db = FakeDB()
    current_user = SimpleNamespace(id="user-1", org_id=7)
    request = SimpleNamespace(
        course_id="course-1",
        section=0,
        section_id=None,
        title="Quiz Module",
        module_type="quiz",
        content_url=None,
    )

    authoring.create_module(request, db=db, current_user=current_user)

    assert len(persist_calls) == 2
    quiz_blocks = [instance for instance, _ in persist_calls if isinstance(instance, DummyLessonBlock)]
    assert len(quiz_blocks) == 1
    assert len(quiz_blocks[0].metadata_json.get("questions", [])) == 1
