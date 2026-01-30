# Flutter / Dart Testing Conventions

## Test Structure

```
test/
├── features/
│   └── user/
│       ├── data/
│       │   ├── datasources/
│       │   │   └── user_remote_data_source_test.dart
│       │   └── repositories/
│       │       └── user_repository_impl_test.dart
│       ├── domain/
│       │   └── usecases/
│       │       └── get_users_test.dart
│       └── presentation/
│           ├── bloc/
│           │   └── user_bloc_test.dart
│           └── pages/
│               └── user_page_test.dart
├── fixtures/
│   └── user_fixture.dart
├── helpers/
│   ├── pump_app.dart
│   └── mocks.dart
└── widget_test.dart
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{file}_test.dart` | `user_bloc_test.dart` |
| Group | Describes class/method | `group('UserBloc')` |
| Test | Describes behavior | `test('emits loaded when successful')` |
| Mock | `Mock{Class}` | `MockUserRepository` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | flutter_test | Built-in |
| Mocking | mocktail | Simple mocking |
| BLoC testing | bloc_test | BLoC-specific |
| Golden tests | golden_toolkit | Screenshot tests |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `flutter test` |
| Run specific | `flutter test test/features/user/` |
| Coverage | `flutter test --coverage` |
| Watch | `flutter test --watch` |
| Golden update | `flutter test --update-goldens` |

## BLoC Tests

```dart
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dartz/dartz.dart';

class MockGetUsersUseCase extends Mock implements GetUsersUseCase {}

void main() {
  late MockGetUsersUseCase mockGetUsersUseCase;
  late UserBloc bloc;

  setUp(() {
    mockGetUsersUseCase = MockGetUsersUseCase();
    bloc = UserBloc(getUsersUseCase: mockGetUsersUseCase);
  });

  tearDown(() {
    bloc.close();
  });

  group('UserBloc', () {
    final users = [User(id: '1', name: 'Test')];

    test('initial state is UserInitial', () {
      expect(bloc.state, const UserInitial());
    });

    blocTest<UserBloc, UserState>(
      'emits [Loading, Loaded] when LoadUsers succeeds',
      build: () {
        when(() => mockGetUsersUseCase())
            .thenAnswer((_) async => Right(users));
        return bloc;
      },
      act: (bloc) => bloc.add(const LoadUsers()),
      expect: () => [
        const UserLoading(),
        UserLoaded(users: users),
      ],
      verify: (_) {
        verify(() => mockGetUsersUseCase()).called(1);
      },
    );

    blocTest<UserBloc, UserState>(
      'emits [Loading, Error] when LoadUsers fails',
      build: () {
        when(() => mockGetUsersUseCase())
            .thenAnswer((_) async => const Left(ServerFailure(message: 'Error')));
        return bloc;
      },
      act: (bloc) => bloc.add(const LoadUsers()),
      expect: () => [
        const UserLoading(),
        const UserError(message: 'Error'),
      ],
    );
  });
}
```

## Widget Tests

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:mocktail/mocktail.dart';

class MockUserBloc extends MockBloc<UserEvent, UserState> implements UserBloc {}

void main() {
  late MockUserBloc mockBloc;

  setUp(() {
    mockBloc = MockUserBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<UserBloc>.value(
        value: mockBloc,
        child: const UserView(),
      ),
    );
  }

  group('UserView', () {
    testWidgets('shows loading indicator when loading', (tester) async {
      when(() => mockBloc.state).thenReturn(const UserLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows users when loaded', (tester) async {
      final users = [User(id: '1', name: 'Test User')];
      when(() => mockBloc.state).thenReturn(UserLoaded(users: users));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Test User'), findsOneWidget);
    });

    testWidgets('shows error message when error', (tester) async {
      when(() => mockBloc.state)
          .thenReturn(const UserError(message: 'Something went wrong'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Something went wrong'), findsOneWidget);
    });

    testWidgets('tapping user navigates to details', (tester) async {
      final users = [User(id: '1', name: 'Test User')];
      when(() => mockBloc.state).thenReturn(UserLoaded(users: users));

      await tester.pumpWidget(buildSubject());
      await tester.tap(find.text('Test User'));
      await tester.pumpAndSettle();

      // Verify navigation occurred
    });
  });
}
```

## Repository Tests

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:dartz/dartz.dart';

class MockUserRemoteDataSource extends Mock implements UserRemoteDataSource {}

void main() {
  late MockUserRemoteDataSource mockRemoteDataSource;
  late UserRepositoryImpl repository;

  setUp(() {
    mockRemoteDataSource = MockUserRemoteDataSource();
    repository = UserRepositoryImpl(remoteDataSource: mockRemoteDataSource);
  });

  group('getUsers', () {
    final userModels = [UserModel(id: '1', name: 'Test', email: 'test@example.com')];

    test('returns users when call is successful', () async {
      when(() => mockRemoteDataSource.getUsers())
          .thenAnswer((_) async => userModels);

      final result = await repository.getUsers();

      expect(result.isRight(), true);
      result.fold(
        (l) => fail('should be right'),
        (r) => expect(r.length, 1),
      );
    });

    test('returns ServerFailure when call throws', () async {
      when(() => mockRemoteDataSource.getUsers())
          .thenThrow(ServerException(message: 'Server error'));

      final result = await repository.getUsers();

      expect(result.isLeft(), true);
      result.fold(
        (l) => expect(l, isA<ServerFailure>()),
        (r) => fail('should be left'),
      );
    });
  });
}
```

## Test Fixtures

```dart
// test/fixtures/user_fixture.dart
class UserFixture {
  static User user({
    String id = '1',
    String name = 'Test User',
    String email = 'test@example.com',
  }) {
    return User(id: id, name: name, email: email);
  }

  static List<User> users({int count = 3}) {
    return List.generate(
      count,
      (i) => user(id: '$i', name: 'User $i'),
    );
  }

  static UserModel userModel({
    String id = '1',
    String name = 'Test User',
    String email = 'test@example.com',
  }) {
    return UserModel(id: id, name: name, email: email);
  }
}
```

## Test Helpers

```dart
// test/helpers/pump_app.dart
extension PumpApp on WidgetTester {
  Future<void> pumpApp(Widget widget) {
    return pumpWidget(
      MaterialApp(
        home: widget,
      ),
    );
  }

  Future<void> pumpAppWithBloc<B extends BlocBase<S>, S>(
    Widget widget,
    B bloc,
  ) {
    return pumpWidget(
      MaterialApp(
        home: BlocProvider<B>.value(
          value: bloc,
          child: widget,
        ),
      ),
    );
  }
}
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on BLoCs, repositories, and use cases
- Test widget behavior, not implementation
