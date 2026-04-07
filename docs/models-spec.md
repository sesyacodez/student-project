1. User (Користувачі: Адміністратори та Вчителі)
------------------------------------------------
Опис: Люди, які мають доступ до системи (персонал). Студенти сюди НЕ входять.
Поля: phone (унікальний логін), password, first_name, last_name, role (ADMIN/TEACHER), is_active.
Зв'язки:
- Many-to-Many з Branch (через проміжну таблицю UserBranch): Адміністратор чи вчитель може належати до кількох філій.
- One-to-Many з Lesson: Вчитель може проводити багато уроків.
- One-to-Many з LessonTemplate: Вчитель може мати багато шаблонів розкладу.

2. Branch (Філія)
------------------------------------------------
Опис: Фізичний навчальний центр (хаб). Усі дані ізольовані в межах філій.
Поля: name, address, city, status (ACTIVE/ARCHIVED).
Зв'язки:
- One-to-Many з Subject: Філія має багато предметів.
- One-to-Many з Student: Філія має багато студентів.
- One-to-Many з Group: Філія має багато груп.
- One-to-Many з SubscriptionPlan: Філія має багато тарифних планів.

3. Subject (Предмет)
------------------------------------------------
Опис: Навчальна дисципліна (Математика, Англійська тощо).
Поля: name, status (ACTIVE/ARCHIVED).
Зв'язки:
- Many-to-One з Branch (Foreign Key): Належить одній філії.
- Many-to-Many з SubscriptionPlan (через PlanSubject): Які предмети покриває план.
- One-to-Many з Lesson та LessonTemplate: Кожен урок стосується одного предмета.

4. Student (Студент)
------------------------------------------------
Опис: Учень, який навчається в центрі. Дані вносяться адміністратором.
Поля: first_name, last_name, dob (дата народження), phone, email, address, 
      parent_name, parent_phone, parent_email, parent_relation, status.
Зв'язки:
- Many-to-One з Branch (Foreign Key): Студент навчається в одній філії.
- Many-to-Many з Group (через GroupStudent): Студент може бути в кількох групах.
- One-to-Many з StudentSubscription: У студента може бути багато підписок на різні предмети.
- One-to-Many з Lesson / LessonTemplate: Для індивідуальних занять.
- One-to-Many з Attendance: Студент має багато записів про відвідуваність.

5. Group (Група)
------------------------------------------------
Опис: Об'єднання студентів для групових занять.
Поля: name, status.
Зв'язки:
- Many-to-One з Branch (Foreign Key): Належить одній філії.
- Many-to-Many з Student (через GroupStudent): Містить багато студентів.
- One-to-Many з Lesson / LessonTemplate: Уроки можуть бути призначені для всієї групи.

6. SubscriptionPlan (План підписки / Тариф)
------------------------------------------------
Опис: Цінова політика. Визначає вартість уроку в залежності від частоти занять.
Поля: name, type (INDIVIDUAL/GROUP), status.
Зв'язки:
- Many-to-One з Branch (Foreign Key): Належить філії.
- Many-to-Many з Subject (через PlanSubject): До яких предметів можна застосувати цей тариф.
- One-to-Many з PricingTier: План має кілька цінових сходинок (tiers).
- One-to-Many з StudentSubscription: Багато студентів можуть користуватися одним планом.

7. PricingTier (Цінова сітка / Сходинка)
------------------------------------------------
Опис: Конкретна ціна за урок при певній кількості уроків на місяць.
Поля: lessons_per_month (напр. 8), price_per_lesson (напр. $19).
Зв'язки:
- Many-to-One з SubscriptionPlan (Foreign Key): Належить конкретному тарифу.

8. StudentSubscription (Підписка студента)
------------------------------------------------
Опис: Факт призначення конкретного тарифу конкретному студенту на конкретний предмет.
Поля: start_date.
Зв'язки:
- Many-to-One з Student (Foreign Key).
- Many-to-One з SubscriptionPlan (Foreign Key).
- Many-to-One з Subject (Foreign Key).

9. LessonTemplate (Шаблон розкладу)
------------------------------------------------
Опис: Правило, за яким система автоматично генеруватиме майбутні уроки (напр. "Пн, Ср на 10:00").
Поля: start_date (початок дії), end_date (кінець дії), days_of_week (Пн, Вт...), start_time, end_time, is_active.
Зв'язки:
- Many-to-One з User (Teacher): Хто викладає.
- Many-to-One з Subject: Що викладають.
- Many-to-One з Student (Foreign Key, null=True): Якщо це шаблон індивідуального уроку.
- Many-to-One з Group (Foreign Key, null=True): Якщо це шаблон групового уроку.

10. Lesson (Урок)
------------------------------------------------
Опис: Фактичний запис про заняття на конкретну дату і час.
Поля: date, start_time, end_time, status (SCHEDULED, COMPLETED, CANCELLED).
Зв'язки:
- Many-to-One з LessonTemplate (Foreign Key, null=True): З якого шаблону згенеровано.
- Many-to-One з User (Teacher): Хто веде.
- Many-to-One з Subject: Який предмет.
- Many-to-One з Student (Foreign Key, null=True): Індивідуальне заняття.
- Many-to-One з Group (Foreign Key, null=True): Групове заняття.
- One-to-Many з Attendance: Кожен урок має список відвідуваності.

11. Attendance (Відвідуваність)
------------------------------------------------
Опис: Фіксація присутності конкретного студента на конкретному уроці.
Поля: status (PRESENT/ABSENT), note (коментар вчителя).
Зв'язки:
- Many-to-One з Lesson (Foreign Key): На якому уроці.
- Many-to-One з Student (Foreign Key): Хто саме зі студентів.
"""