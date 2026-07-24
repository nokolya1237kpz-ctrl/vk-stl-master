import React from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  EmptyState,
  HeroCard,
  IconButton,
  Input,
  Loader,
  MetricCard,
  Modal,
  Panel,
  Section,
  Skeleton,
  StatCard,
  Textarea,
} from "../index.js";
import "../styles/ui.css";

export function Demo() {
  return (
    <Container>
      <Section
        number="UI"
        kicker="STL Master Kit"
        title="Базовые компоненты"
        description="Изолированный стенд компонентов для будущей миграции интерфейса."
      >
        <Card>
          <Button>Основная кнопка</Button>
          <Button variant="secondary">Вторичная</Button>
          <Button variant="outline">Контурная</Button>
          <Button variant="ghost">Текстовая</Button>
          <Button variant="danger">Опасная</Button>
        </Card>

        <Divider />

        <Card interactive>
          <Badge variant="primary">Premium</Badge>
          <Badge variant="success">Готово</Badge>
          <Badge variant="warning">Проверка</Badge>
          <Badge variant="danger">Ошибка</Badge>
        </Card>

        <Panel title="Панель">
          <Input label="Название модели" placeholder="Dragon_Skull.stl" />
          <Textarea label="Комментарий" placeholder="Описание операции" />
        </Panel>

        <HeroCard title="Быстро" text="AI-проверка и подготовка модели" icon="*" />
        <StatCard value="99.9%" label="Успешных обработок" />
        <MetricCard value="2 853 184" label="Треугольников" delta="-60.6%" />
        <IconButton label="Настройки">...</IconButton>
        <Loader />
        <Skeleton height="48px" />
        <EmptyState title="Нет данных" description="Здесь появятся результаты после обработки." />
        <Modal open title="Каркас модального окна" footer={<Button>Готово</Button>}>
          Содержимое модального окна без бизнес-логики.
        </Modal>
      </Section>
    </Container>
  );
}
