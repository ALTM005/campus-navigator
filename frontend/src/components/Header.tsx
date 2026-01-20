// src/components/Header.tsx
type Props = { health: string };
export default function Header({ health }: Props) {
  return (
    <header className="appbar">
      <h1>Campus Navigator</h1>
    </header>
  );
}
