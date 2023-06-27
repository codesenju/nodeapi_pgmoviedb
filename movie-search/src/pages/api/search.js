import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_APP_API_URL,
});

export default async function handler(req, res) {

  const { searchTerm } = req.query;

  try {
    const response = await api.get(`movies/${searchTerm}`);
    console.log("Server side:")
    console.log(response.data.baseURL)
    const data = response.data;
    res.status(200).json(data);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    res.status(500).json({ message: 'Server Side Error: Unable to connect to the server. Please try again later.' });
  }
  
}
