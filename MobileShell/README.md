Это новый проект на [**React Native**](https://reactnative.dev), созданный с помощью [`@react-native-community/cli`](https://github.com/react-native-community/cli).

# Начало работы

>**Примечание**: Перед продолжением убедитесь, что вы выполнили инструкцию [React Native - Environment Setup](https://reactnative.dev/docs/environment-setup) до шага "Creating a new application".

## Шаг 1: Запустите сервер Metro

Сначала нужно запустить **Metro** — JavaScript _бандлер_, который поставляется _вместе с_ React Native.

Чтобы запустить Metro, выполните следующую команду из _корня_ проекта React Native:

```bash
# через npm
npm start

# ИЛИ через Yarn
yarn start
```

## Шаг 2: Запустите приложение

Оставьте Metro Bundler работать в _отдельном_ терминале. Затем откройте _новый_ терминал из _корня_ вашего React Native проекта. Выполните следующую команду, чтобы запустить приложение для _Android_ или _iOS_:

### Для Android

```bash
# через npm
npm run android

# ИЛИ через Yarn
yarn android
```

### Для iOS

```bash
# через npm
npm run ios

# ИЛИ через Yarn
yarn ios
```

Если все настроено _правильно_, через некоторое время вы увидите запущенное приложение в _Android Emulator_ или _iOS Simulator_ (при условии, что эмулятор/симулятор тоже настроен корректно).

Это один из способов запуска приложения — также можно запускать его напрямую из Android Studio и Xcode соответственно.

## Шаг 3: Изменение приложения

Теперь, когда приложение успешно запущено, давайте внесем изменения.

1. Откройте `App.tsx` в любом удобном текстовом редакторе и измените несколько строк.
2. Для **Android**: дважды нажмите клавишу <kbd>R</kbd> или выберите **"Reload"** в **Developer Menu** (<kbd>Ctrl</kbd> + <kbd>M</kbd> (в Windows и Linux) или <kbd>Cmd ⌘</kbd> + <kbd>M</kbd> (в macOS)), чтобы увидеть изменения.

   Для **iOS**: нажмите <kbd>Cmd ⌘</kbd> + <kbd>R</kbd> в iOS Simulator, чтобы перезагрузить приложение и увидеть изменения.

## Поздравляем! :tada:

Вы успешно запустили и изменили свое React Native приложение. :partying_face:

### Что дальше?

- Если вы хотите добавить этот новый React Native код в существующее приложение, посмотрите [Integration guide](https://reactnative.dev/docs/integration-with-existing-apps).
- Если хотите узнать о React Native больше, посмотрите [Introduction to React Native](https://reactnative.dev/docs/getting-started).

# Устранение неполадок

Если что-то не работает, откройте страницу [Troubleshooting](https://reactnative.dev/docs/troubleshooting).

# Узнать больше

Чтобы глубже изучить React Native, посмотрите следующие ресурсы:

- [React Native Website](https://reactnative.dev) - подробнее о React Native.
- [Getting Started](https://reactnative.dev/docs/environment-setup) - **обзор** React Native и того, как настроить окружение.
- [Learn the Basics](https://reactnative.dev/docs/getting-started) - **пошаговое введение** в **основы** React Native.
- [Blog](https://reactnative.dev/blog) - последние официальные публикации в **блоге** React Native.
- [`@facebook/react-native`](https://github.com/facebook/react-native) - Open Source **репозиторий** React Native на GitHub.
