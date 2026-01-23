import { ConflictException, Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from './schemas/user.schema';
import * as bcrypt from 'bcrypt';

@Injectable()
export class UsersService {
  constructor(@InjectModel(User.name) private userModel: Model<User>) {}

  async create(email: string, pass: string, name: string): Promise<User> {
    // Verificar si el usuario ya existe
    const exists = await this.userModel.findOne({ email });
    if (exists) throw new ConflictException('El correo ya esta registrado');

    // Encriptar password
    const hashedPassword = await bcrypt.hash(pass, 10);

    const newUser = new this.userModel({
      email,
      password: hashedPassword,
      name,
    });
    return newUser.save();
  }

  async findByEmail(email: string): Promise<User | undefined> {
    const user = await this.userModel.findOne({ email }).exec();
    return user ?? undefined;
  }
}
