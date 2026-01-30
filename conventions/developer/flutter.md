# Flutter / Dart Conventions

## Project Structure

```
lib/
├── core/
│   ├── constants/
│   ├── error/
│   ├── network/
│   └── utils/
├── features/
│   └── user/
│       ├── data/
│       │   ├── datasources/
│       │   ├── models/
│       │   └── repositories/
│       ├── domain/
│       │   ├── entities/
│       │   ├── repositories/
│       │   └── usecases/
│       └── presentation/
│           ├── bloc/              # or providers/
│           ├── pages/
│           └── widgets/
├── injection.dart                 # DI setup
└── main.dart
test/
├── features/
│   └── user/
│       ├── data/
│       ├── domain/
│       └── presentation/
└── fixtures/
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| File | snake_case | `user_repository.dart` |
| Class | PascalCase | `UserRepository` |
| Function | camelCase | `fetchUser` |
| Variable | camelCase | `userName` |
| Constant | lowerCamelCase | `defaultTimeout` |
| Private | _prefix | `_privateMethod` |
| Widget | PascalCase | `UserCard` |
| BLoC | PascalCase + Bloc | `UserBloc` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| State management | flutter_bloc or Riverpod | BLoC for large apps |
| DI | get_it + injectable | Service locator |
| Networking | dio | HTTP client |
| JSON | freezed + json_serializable | Immutable models |
| Navigation | go_router | Declarative routing |
| Storage | hive or drift | Local database |
| Testing | flutter_test + mocktail | Built-in + mocking |

## Build Commands

| Action | Command |
|--------|---------|
| Run | `flutter run` |
| Build APK | `flutter build apk` |
| Build iOS | `flutter build ios` |
| Test | `flutter test` |
| Analyze | `flutter analyze` |
| Format | `dart format .` |
| Generate | `flutter pub run build_runner build` |

## Widget Pattern

```dart
// presentation/pages/user_page.dart
class UserPage extends StatelessWidget {
  const UserPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (context) => getIt<UserBloc>()..add(const LoadUsers()),
      child: const UserView(),
    );
  }
}

class UserView extends StatelessWidget {
  const UserView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Users')),
      body: BlocBuilder<UserBloc, UserState>(
        builder: (context, state) {
          return switch (state) {
            UserLoading() => const Center(child: CircularProgressIndicator()),
            UserError(:final message) => ErrorWidget(message: message),
            UserLoaded(:final users) => UserList(users: users),
          };
        },
      ),
    );
  }
}

// presentation/widgets/user_list.dart
class UserList extends StatelessWidget {
  const UserList({super.key, required this.users});

  final List<User> users;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: users.length,
      itemBuilder: (context, index) {
        final user = users[index];
        return UserCard(
          user: user,
          onTap: () => context.push('/users/${user.id}'),
        );
      },
    );
  }
}
```

## BLoC Pattern

```dart
// presentation/bloc/user_bloc.dart
part 'user_event.dart';
part 'user_state.dart';

class UserBloc extends Bloc<UserEvent, UserState> {
  UserBloc({required this.getUsersUseCase}) : super(const UserInitial()) {
    on<LoadUsers>(_onLoadUsers);
    on<RefreshUsers>(_onRefreshUsers);
  }

  final GetUsersUseCase getUsersUseCase;

  Future<void> _onLoadUsers(LoadUsers event, Emitter<UserState> emit) async {
    emit(const UserLoading());

    final result = await getUsersUseCase();

    result.fold(
      (failure) => emit(UserError(message: failure.message)),
      (users) => emit(UserLoaded(users: users)),
    );
  }

  Future<void> _onRefreshUsers(RefreshUsers event, Emitter<UserState> emit) async {
    final result = await getUsersUseCase();

    result.fold(
      (failure) => emit(UserError(message: failure.message)),
      (users) => emit(UserLoaded(users: users)),
    );
  }
}

// presentation/bloc/user_event.dart
part of 'user_bloc.dart';

sealed class UserEvent {
  const UserEvent();
}

final class LoadUsers extends UserEvent {
  const LoadUsers();
}

final class RefreshUsers extends UserEvent {
  const RefreshUsers();
}

// presentation/bloc/user_state.dart
part of 'user_bloc.dart';

sealed class UserState {
  const UserState();
}

final class UserInitial extends UserState {
  const UserInitial();
}

final class UserLoading extends UserState {
  const UserLoading();
}

final class UserLoaded extends UserState {
  const UserLoaded({required this.users});
  final List<User> users;
}

final class UserError extends UserState {
  const UserError({required this.message});
  final String message;
}
```

## Model with Freezed

```dart
// data/models/user_model.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    required String id,
    required String name,
    required String email,
    @Default(false) bool isActive,
  }) = _UserModel;

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);
}
```

## Repository Pattern

```dart
// domain/repositories/user_repository.dart
abstract class UserRepository {
  Future<Either<Failure, List<User>>> getUsers();
  Future<Either<Failure, User>> getUser(String id);
}

// data/repositories/user_repository_impl.dart
class UserRepositoryImpl implements UserRepository {
  UserRepositoryImpl({required this.remoteDataSource});

  final UserRemoteDataSource remoteDataSource;

  @override
  Future<Either<Failure, List<User>>> getUsers() async {
    try {
      final models = await remoteDataSource.getUsers();
      return Right(models.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    }
  }
}
```

## Code Style

- Use `const` constructors wherever possible
- Prefer composition over inheritance
- Use sealed classes for states/events (Dart 3)
- Follow Clean Architecture layers
- Keep widgets small and focused
- Extract reusable widgets
- Use proper null safety
- Avoid dynamic typing
