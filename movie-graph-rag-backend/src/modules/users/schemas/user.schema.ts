import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

export class FavoriteMovieSnapshot {
  uri: string;
  title: string;
  posterUrl?: string;
  year?: number;
  runtime?: number;
  certification?: string;
  director?: string;
  genres?: string[];
  description?: string;
  rating?: number;
  relationReason?: string;
  addedAt?: Date;
}

@Schema({ timestamps: true })
export class User extends Document {
  @Prop({ unique: true, required: true })
  email: string;

  @Prop({ required: true })
  password: string;

  @Prop({ required: true })
  name: string;

  @Prop({
    type: [
      {
        uri: { type: String, required: true },
        title: { type: String, required: true },
        posterUrl: { type: String },
        year: { type: Number },
        runtime: { type: Number },
        certification: { type: String },
        director: { type: String },
        genres: { type: [String], default: [] },
        description: { type: String },
        rating: { type: Number },
        relationReason: { type: String },
        addedAt: { type: Date, default: Date.now },
      },
    ],
    default: [],
  })
  favoriteMovies: FavoriteMovieSnapshot[];
}

export const UserSchema = SchemaFactory.createForClass(User);
