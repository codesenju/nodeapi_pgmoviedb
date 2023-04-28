import MovieSearch from '../components/MovieSearch';
import { Container } from 'react-bootstrap';

export default function Home() {
  return (
    <Container>
      <h1 className="text-center my-4">Movie Search</h1>
      <MovieSearch />
    </Container>
  );
}
