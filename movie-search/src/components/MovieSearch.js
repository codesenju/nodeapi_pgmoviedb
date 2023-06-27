import { useState } from 'react';
import { Table } from 'react-bootstrap';
import styles from '../styles/MovieSearch.module.css';
//import axios from 'axios';

//const api = axios.create({
//  baseURL: process.env.NEXT_APP_API_URL,
//});

export default function MovieSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const [movieData, setMovieData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    try {
      // const response = await fetch(`http://localhost:3000/api/search?searchTerm=${searchTerm}`);
      const response = await fetch(`/api/search?searchTerm=${searchTerm}`);
      //const response = await api.get(`/api/search?searchTerm=${searchTerm}`);
      if (!response.ok) {
        throw new Error(`Unable to connect to the server. Please try again later.`);
      }
      console.log("Client side:")
      console.log(response.url)
      const data = await response.json();
      // const data = response.data;
      setMovieData(data);
      setIsLoading(false);
      setError(null);
      setSearched(true);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      setIsLoading(false);
      setError(error.message);
    }
  };

  const isSearchDisabled = searchTerm.length === 0;

  return (
    <div className={styles.container}>
      <form className={styles.form} onSubmit={handleSearch}>
        <input className={styles.input} type="text" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
        <button className={`${styles.button} ${isSearchDisabled ? styles.disabled : ''}`} type="submit" disabled={isSearchDisabled}>Search</button>
      </form>
      {isLoading && <p>Loading...</p>}
      {error && <p className={styles.error}>{error}</p>}
      {searched && movieData.length > 0 ? (
        <Table className={styles.table} striped bordered hover>
          <thead>
            <tr>
              <th>Title</th>
              <th>Year</th>
              <th>Runtime</th>
              <th>Genres</th>
            </tr>
          </thead>
          <tbody>
            {movieData.map((movie) => (
              <tr key={movie.tconst}>
                <td>{movie.primarytitle}</td>
                <td>{movie.startyear}</td>
                <td>{movie.runtimeminutes} minutes</td>
                <td>{movie.genres}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : searched && movieData.length === 0 ? (
        <p>No results found.</p>
      ) : null}
    </div>
  );
}
