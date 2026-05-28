import TodoPost from "./TodoPost";
import { useEffect, useState } from "react";
import axios from "axios";
import { useQuery } from "@tanstack/react-query";

type Todo = {
  id: number;
  title: string;
  organization: string;
  organizationTypes: string;
  volunteerTypes: string;
  commitment: string;
  location: string;
  applicationDeadline: string;
  website: string;
  distance: number;
};

interface TodoListProps {
  searchTerm: string;
  locationFilter: string;
  maxTime: number;
}

function TodoList({ searchTerm, locationFilter, maxTime }: TodoListProps) {
  const [todos, setTodos] = useState<Todo[]>([
    {
      id: 1,
      title: "Web Developer & Research Assistant",
      organization: "@ Spill The Code",
      organizationTypes: "Education, Children, Youth and Family",
      volunteerTypes:
        "Arts, Crafts and Photography, Communications and Marketing",
      commitment: "Short term (less than 6 months)",
      location: "Ottawa - West",
      applicationDeadline: "April 30, 2025",
      website: "TO BE DETERMINED",
      distance: 1200,
    },
    {
      id: 2,
      title: "Graphic Designer",
      organization: "Creative Commons",
      organizationTypes: "Arts and Culture",
      volunteerTypes: "Design, Digital Media",
      commitment: "Flexible",
      location: "Remote",
      applicationDeadline: "May 15, 2025",
      website: "https://example.com",
      distance: 3600, // 1 hour
    },
    {
      id: 3,
      title: "Community Organizer",
      organization: "Local Initiatives",
      organizationTypes: "Community Development",
      volunteerTypes: "Event Planning, Outreach",
      commitment: "Long term (more than 6 months)",
      location: "Ottawa - West",
      applicationDeadline: "June 1, 2025",
      website: "https://example.org",
      distance: 7200, // 2 hours
    },
  ]);

  const retrievePosts = async () => {
    const response = await axios.get(
      "https://jsonplaceholder.typicode.com/posts"
    );
    return response;
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ["postsData"],
    queryFn: retrievePosts,
  });

  useEffect(() => {
    if (data && Array.isArray(data)) {
      setTodos((prevTodos) => [...prevTodos, ...data]);
    }
  }, [data]);

  const filteredTodos = todos.filter((todo) => {
    const matchesSearch =
      searchTerm === "" ||
      todo.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      todo.organization.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesLocation =
      locationFilter === "" || todo.location === locationFilter;

    const todoTimeInMinutes = Math.ceil(todo.distance / 60);
    const matchesTime = todoTimeInMinutes <= maxTime;

    return matchesSearch && matchesLocation && matchesTime;
  });

  if (isLoading) return <div>Fetching posts...</div>;
  if (error) return <div>An error occurred: {error.message}</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      {filteredTodos.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-lg text-gray-500">
            No opportunities match your filters.
          </p>
          <p className="text-sm text-gray-400">
            Try adjusting your search criteria.
          </p>
        </div>
      ) : (
        <div className="text-center">
          {filteredTodos.map((todo) => (
            <TodoPost
              key={todo.id}
              id={todo.id}
              title={todo.title}
              organization={todo.organization}
              organizationTypes={todo.organizationTypes}
              volunteerTypes={todo.volunteerTypes}
              commitment={todo.commitment}
              location={todo.location}
              applicationDeadline={todo.applicationDeadline}
              website={todo.website}
              distance={todo.distance}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default TodoList;
